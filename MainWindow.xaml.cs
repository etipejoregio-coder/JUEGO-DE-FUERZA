using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Media.Effects;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using DesafioTiempoReaccion.GameEngine;

namespace DesafioTiempoReaccion.Ui;

public partial class MainWindow : Window
{
    private enum Modo { Reaccion, TiempoObjetivo, Empuje }

    private static readonly Color ColRojo = Color.FromRgb(0xFF, 0x3A, 0x3A);
    private static readonly Color ColAzul = Color.FromRgb(0x2F, 0x7B, 0xFF);
    private static readonly Color ColVerde = Color.FromRgb(0x1F, 0xD8, 0x5A);
    private static readonly Color ColOro = Color.FromRgb(0xFF, 0xD2, 0x1F);
    private static readonly Color ColCian = Color.FromRgb(0x3C, 0x9C, 0xFF);

    private static readonly Key[] TeclasReservadas =
        { Key.Space, Key.Enter, Key.Escape, Key.F1, Key.F11, Key.Tab, Key.System, Key.Left, Key.Right };

    private readonly GameSettings _settings = GameSettings.Load();
    private readonly GameEngine.GameEngine _engine;
    private readonly TargetTimeEngine _target = new();
    private readonly Voz _voz = new();
    private readonly Musica _musica = new();
    private readonly DispatcherTimer _timer;
    private readonly Efectos _efectos = new();
    private Modo _modo = Modo.Empuje;

    // ---- Modo Empuje ----
    private readonly PushEngine _push = new();
    private readonly long[] _ultimoPulso = new long[2];
    private const double AnchoD = 1559, AltoD = 1009, MargenLinea = 50, X0 = 750, Amplitud = 470, KEmpuje = 25;
    private double _bx = X0, _bxObjetivo = X0;
    private static readonly (double dx, double fy)[] Rayo =
    {
        (30, -0.02), (-25, 0.10), (35, 0.22), (-40, 0.34), (20, 0.45),
        (-35, 0.58), (40, 0.70), (-25, 0.82), (15, 0.92), (0, 1.02)
    };
    private readonly Dictionary<string, string> _cfgFondos = new();
    private readonly Dictionary<string, TextBlock> _cfgFondoTxt = new();
    private readonly Dictionary<string, string> _cfgSonidos = new();
    private readonly Dictionary<string, TextBlock> _cfgSonidoTxt = new();
    private static readonly (string Slot, string Nombre)[] Slots =
    {
        ("cuenta", "Cuenta 3-2-1"), ("ahora", "¡Ahora!"), ("detener", "Al detener"), ("ganador", "Ganador")
    };
    private string _cfgMusica = "";
    private bool _fullscreen;

    public MainWindow()
    {
        InitializeComponent();

        _engine = new GameEngine.GameEngine(_settings);
        _engine.StateChanged += OnStateChanged;
        _engine.RoundFinished += OnRoundFinished;
        _engine.TimedOut += OnTimedOut;

        _target.StateChanged += OnTargetState;
        _target.CountdownTick += OnTargetCountdown;
        _target.TeamStopped += OnTargetStopped;
        _target.Finished += OnTargetFinished;
        _target.TargetChanged += OnTargetChanged;

        _push.StateChanged += OnPushState;
        _push.CountdownTick += OnPushCountdown;
        _push.Pushed += OnPushed;
        _push.Finished += OnPushFinished;
        _push.DurationChanged += OnPushDuration;

        CargarFondos();

        _timer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(16) };
        _timer.Tick += (_, _) => OnTick();
        _timer.Start();

        _target.MargenMs = _settings.MargenAciertoSegundos * 1000.0;

        // Manecilla del cronómetro: gira siempre, solo como decoración
        ManoReloj.BeginAnimation(RotateTransform.AngleProperty,
            new DoubleAnimation(0, 360, TimeSpan.FromSeconds(3)) { RepeatBehavior = RepeatBehavior.Forever });

        AplicarModo();
    }

    protected override void OnClosed(EventArgs e)
    {
        _musica.Detener();
        _voz.Dispose();
        base.OnClosed(e);
    }

    // ------------------------------------------------------------------
    //  MODO 1: Tiempo de reacción (eventos del motor)
    // ------------------------------------------------------------------
    private void OnStateChanged(GameState state)
    {
        switch (state)
        {
            case GameState.CuentaRegresiva:
                ResetDisplays();
                SetBanner("¡PREPÁRATE!", "No presiones hasta ver la señal", ColOro, 46);
                break;
            case GameState.EsperandoSenal:
                SetBanner("ESPERA LA SEÑAL…", "Quien presione antes pierde el punto", ColCian, 40);
                break;
            case GameState.RondaActiva:
                SetBanner("¡AHORA!", "¡PRESIONA YA!", ColVerde, 88, 0xCC);
                _efectos.Reproducir("ahora", _settings.SonidoAhora);
                break;
        }
    }

    private void OnRoundFinished(ReactionRoundResult r)
    {
        ActualizarMarcadores(_engine.PuntosRojo, _engine.PuntosAzul);

        bool rojo = r.Winner == Team.Rojo;
        string nombre = rojo ? "ROJO" : "AZUL";
        Color color = rojo ? ColRojo : ColAzul;

        if (r.FalseStart)
        {
            (r.Infractor == Team.Rojo ? DispRojo : DispAzul).Text = "--.--";
            DispCentral.Text = "--.--";
            SetBanner($"¡GANA EL EQUIPO {nombre}!",
                      $"Salida en falso del equipo {(rojo ? "azul" : "rojo")}\nESPACIO para otra ronda", color, 38, 0x88);
        }
        else
        {
            string t = FormatSeconds(r.ReactionTimeMs);
            (rojo ? DispRojo : DispAzul).Text = t;
            DispCentral.Text = t;
            SetBanner($"¡GANA EL EQUIPO {nombre}!",
                      $"{r.ReactionTimeMs:F0} ms\nESPACIO para otra ronda", color, 38, 0x88);
        }

        _efectos.Reproducir("ganador", _settings.SonidoGanador);
        PulsarMarcador(r.Winner);
    }

    private void OnTimedOut() =>
        SetBanner("TIEMPO AGOTADO", "Nadie presionó a tiempo\nESPACIO para otra ronda", ColOro, 40);

    // ------------------------------------------------------------------
    //  MODO 2: Tiempo objetivo (eventos del motor)
    // ------------------------------------------------------------------
    private void OnTargetState(GameState state)
    {
        switch (state)
        {
            case GameState.CuentaRegresiva:
                ResetDisplays();
                SetBanner("¡PREPÁRATE!", "Escucha la cuenta regresiva", ColOro, 46);
                break;
            case GameState.RondaActiva:
                SetBanner("¡AHORA!", $"Detente en {FormatTarget()}\nRojo: tecla 1 · Azul: tecla 2", ColVerde, 88, 0xCC);
                _musica.Reproducir(_settings.MusicaPath);
                break;
        }
    }

    private void OnTargetCountdown(int n)
    {
        if (n > 0)
        {
            SetBanner(n.ToString(CultureInfo.InvariantCulture), "", ColOro, 100);
            if (_settings.UsarVoz) _voz.Decir(n.ToString(CultureInfo.InvariantCulture));
            else _efectos.Reproducir("cuenta", _settings.SonidoCuenta);
        }
        else
        {
            if (_settings.UsarVoz) _voz.Decir("¡Ahora!");
            _efectos.Reproducir("ahora", _settings.SonidoAhora);
        }
    }

    private void OnTargetStopped(Team team, double ms)
    {
        (team == Team.Rojo ? DispRojo : DispAzul).Text = FormatTime(ms);
        (team == Team.Rojo ? BadgeRojo : BadgeAzul).Visibility = Visibility.Visible;
        _efectos.Reproducir("detener", _settings.SonidoDetener);
    }

    private void OnTargetFinished(TargetTimeResult r)
    {
        _musica.Detener();
        ActualizarMarcadores(_target.PuntosRojo, _target.PuntosAzul);

        string diffs = $"ROJO {Diff(r.RojoMs, r.ObjetivoMs)} · AZUL {Diff(r.AzulMs, r.ObjetivoMs)}\nESPACIO para otra ronda";
        string msg;
        if (r.Winner == Team.Rojo) { msg = "¡Ganó el Equipo Rojo!"; SetBanner(msg.ToUpperInvariant(), diffs, ColRojo, 38, 0x88); }
        else if (r.Winner == Team.Azul) { msg = "¡Ganó el Equipo Azul!"; SetBanner(msg.ToUpperInvariant(), diffs, ColAzul, 38, 0x88); }
        else if (r.RojoAcerto && r.AzulAcerto) { msg = "¡Empate!"; SetBanner("¡EMPATE!", diffs, ColOro, 46, 0x88); }
        else
        {
            msg = "Nadie acertó";
            string margen = _settings.MargenAciertoSegundos.ToString("0.##", CultureInfo.InvariantCulture);
            SetBanner("¡NADIE ACERTÓ!", $"Había que detenerse en {FormatTarget()} (± {margen} s)\n{diffs}", ColOro, 42, 0x88);
        }

        if (_settings.UsarVoz) _voz.Decir(msg);
        _efectos.Reproducir("ganador", _settings.SonidoGanador);
        if (r.Winner != null) PulsarMarcador(r.Winner.Value);
    }

    private void OnTargetChanged()
    {
        DispCentral.Text = FormatTarget();
        ActualizarSelector();
    }

    /// <summary>La caja de abajo (◀ ▶) muestra el objetivo y lo cambia de 5 en 5 min.</summary>
    private void ActualizarSelector()
    {
        TxtModo.Text = _modo == Modo.TiempoObjetivo ? "OBJETIVO  " + FormatTarget() : "TIEMPO DE REACCIÓN";
    }

    private static string Diff(double ms, double objetivoMs)
    {
        double d = ms - objetivoMs;
        string signo = d < 0 ? "-" : "+";
        double a = Math.Abs(d);
        return a >= 60000
            ? signo + FormatTime(a)
            : signo + (a / 1000.0).ToString("0.00", CultureInfo.InvariantCulture) + " s";
    }

    // ------------------------------------------------------------------
    //  Reloj de pantalla
    // ------------------------------------------------------------------
    private void OnTick()
    {
        if (_modo == Modo.Empuje) { TickEmpuje(); return; }

        if (_modo == Modo.Reaccion)
        {
            if (_engine.State != GameState.RondaActiva) return;
            double ms = _engine.ElapsedMs;
            DispCentral.Text = FormatSeconds(ms);
        }
        else
        {
            if (_target.State != GameState.RondaActiva) return;
            double ms = _target.ElapsedMs;
            if (!_target.RojoListo) DispRojo.Text = FormatTime(ms);
            if (!_target.AzulListo) DispAzul.Text = FormatTime(ms);
        }
    }

    // ------------------------------------------------------------------
    //  Acciones
    // ------------------------------------------------------------------
    private bool RondaEnCurso =>
        _engine.State is GameState.CuentaRegresiva or GameState.EsperandoSenal or GameState.RondaActiva
        || _target.State is GameState.CuentaRegresiva or GameState.RondaActiva
        || _push.State is GameState.CuentaRegresiva or GameState.RondaActiva;

    private void IniciarRonda()
    {
        switch (_modo)
        {
            case Modo.Reaccion: _ = _engine.StartRoundAsync(); break;
            case Modo.TiempoObjetivo: _ = _target.StartAsync(); break;
            default: _ = _push.StartAsync(); break;
        }
    }

    private void Presionar(Team t)
    {
        if (!PasaAntirrebote(t)) return;
        VisualBoton(t, true);
        switch (_modo)
        {
            case Modo.Reaccion: _engine.RegisterPress(t); break;
            case Modo.TiempoObjetivo: _target.Stop(t); break;
            default: _push.Push(t); break;
        }
    }

    /// <summary>Con "Usar pulsador" activo se ignoran los rebotes del microswitch (pulsos demasiado seguidos).</summary>
    private bool PasaAntirrebote(Team t)
    {
        if (!_settings.UsarPulsador) return true;
        long ahora = Stopwatch.GetTimestamp();
        int i = t == Team.Rojo ? 0 : 1;
        if ((ahora - _ultimoPulso[i]) * 1000.0 / Stopwatch.Frequency < 35) return false;
        _ultimoPulso[i] = ahora;
        return true;
    }

    private void Reiniciar()
    {
        _musica.Detener();
        _engine.ResetGame();
        _target.ResetGame();
        _push.ResetGame();
        _bxObjetivo = X0;
        ActualizarMarcadores(0, 0);
        ResetDisplays();
        MostrarInicio();
    }

    private void CambiarModo()
    {
        if (RondaEnCurso) return;     // no se cambia de modo en mitad de una ronda
        _modo = _modo switch { Modo.Empuje => Modo.TiempoObjetivo, Modo.TiempoObjetivo => Modo.Reaccion, _ => Modo.Empuje };
        Reiniciar();
        AplicarModo();
    }

    private void AplicarModo()
    {
        bool emp = _modo == Modo.Empuje;
        PantallaClasica.Visibility = emp ? Visibility.Collapsed : Visibility.Visible;
        PantallaEmpuje.Visibility = emp ? Visibility.Visible : Visibility.Collapsed;

        bool t = _modo == Modo.TiempoObjetivo;
        TxtEtiquetaCentral.Text = t ? "TIEMPO OBJETIVO" : "TIEMPO DE REACCIÓN";
        ActualizarSelector();
        AplicarConfiguracion();
        ResetDisplays();
        if (emp)
        {
            _bx = _bxObjetivo = X0;
            PosicionarEscena();
            ActualizarRelojEmpuje();
        }
        MostrarInicio();
    }

    private void MostrarInicio()
    {
        if (_modo == Modo.Empuje)
        {
            MostrarMensajeEmpuje("", "Ajusta el tiempo con ◀ ▶ y pulsa ESPACIO", Colors.White, 120);
            return;
        }
        if (_modo == Modo.Reaccion)
            SetBanner("ESPERA LA SEÑAL Y PRESIONA EL BOTÓN LO MÁS RÁPIDO POSIBLE", "Pulsa ESPACIO para comenzar", ColCian, 28);
        else
            SetBanner("AJUSTA EL TIEMPO OBJETIVO CON ◀ ▶", "Pulsa ESPACIO para comenzar", ColCian, 30);
    }

    private void ResetDisplays()
    {
        bool t = _modo == Modo.TiempoObjetivo;
        DispRojo.Text = DispAzul.Text = t ? "00:00.00" : "00.00";
        DispCentral.Text = t ? FormatTarget() : "00.00";
        BadgeRojo.Visibility = BadgeAzul.Visibility = Visibility.Collapsed;
    }

    private void ActualizarMarcadores(int rojo, int azul)
    {
        TxtPuntosRojo.Text = TxtPuntosRojoE.Text = rojo.ToString(CultureInfo.InvariantCulture);
        TxtPuntosAzul.Text = TxtPuntosAzulE.Text = azul.ToString(CultureInfo.InvariantCulture);
    }

    private void SetBanner(string titulo, string sub, Color acento, double tamano, byte alfaFondo = 0x55)
    {
        TxtMensaje.Text = titulo;
        TxtMensaje.FontSize = Math.Max(14, tamano * 0.58);
        TxtSub.Text = sub;
        CajaSenal.BorderBrush = new SolidColorBrush(acento);
        CajaSenal.Background = new SolidColorBrush(Color.FromArgb(alfaFondo, acento.R, acento.G, acento.B));
        CajaSenal.Effect = new DropShadowEffect { Color = acento, BlurRadius = 30, ShadowDepth = 0, Opacity = 0.8 };
    }

    private void PulsarMarcador(Team t)
    {
        var st = _modo == Modo.Empuje
            ? (t == Team.Rojo ? ScaleMarcadorRojoE : ScaleMarcadorAzulE)
            : (t == Team.Rojo ? ScaleMarcadorRojo : ScaleMarcadorAzul);
        var anim = new DoubleAnimation(1.0, 1.25, TimeSpan.FromMilliseconds(160))
        {
            AutoReverse = true,
            RepeatBehavior = new RepeatBehavior(3)
        };
        st.BeginAnimation(ScaleTransform.ScaleXProperty, anim);
        st.BeginAnimation(ScaleTransform.ScaleYProperty, anim);
    }

    private void VisualBoton(Team t, bool abajo)
    {
        (t == Team.Rojo ? PulsoRojo : PulsoAzul).Opacity = abajo ? 0.3 : 0.0;
    }

    // ------------------------------------------------------------------
    //  MODO 3: Empuje (tira y afloja)
    // ------------------------------------------------------------------
    private void OnPushState(GameState state)
    {
        switch (state)
        {
            case GameState.CuentaRegresiva:
                _bxObjetivo = X0;
                MostrarMensajeEmpuje("¡PREPÁRATE!", "", Colors.White, 100);
                break;
            case GameState.RondaActiva:
                _musica.Reproducir(_settings.MusicaPath);
                MostrarMensajeEmpuje("¡EMPUJA!", "", Color.FromRgb(0x7C, 0xFF, 0x2B), 120);
                _ = OcultarMensajeTrasAsync(1300);
                break;
        }
    }

    private void OnPushCountdown(int n)
    {
        if (n > 0)
        {
            MostrarMensajeEmpuje(n.ToString(CultureInfo.InvariantCulture), "", Colors.White, 220);
            if (_settings.UsarVoz) _voz.Decir(n.ToString(CultureInfo.InvariantCulture));
            else _efectos.Reproducir("cuenta", _settings.SonidoCuenta);
        }
        else
        {
            if (_settings.UsarVoz) _voz.Decir("¡Ahora!");
            _efectos.Reproducir("ahora", _settings.SonidoAhora);
        }
    }

    private void OnPushed(Team team) => _bxObjetivo = X0 + Amplitud * Math.Tanh(_push.Net / KEmpuje);

    private void OnPushDuration() => ActualizarRelojEmpuje();

    private void OnPushFinished(PushResult r)
    {
        _musica.Detener();
        ActualizarMarcadores(_push.PuntosRojo, _push.PuntosAzul);
        _bxObjetivo = X0 + Amplitud * Math.Tanh(_push.Net / KEmpuje);

        string sub = $"Empujes: ROJO {r.EmpujesRojo} · AZUL {r.EmpujesAzul}\nESPACIO para otra ronda";
        string voz;
        if (r.Winner == Team.Rojo) { voz = "¡Ganó el Equipo Rojo!"; MostrarMensajeEmpuje(voz.ToUpperInvariant(), sub, Color.FromRgb(0xFF, 0x7A, 0xD8), 84); }
        else if (r.Winner == Team.Azul) { voz = "¡Ganó el Equipo Azul!"; MostrarMensajeEmpuje(voz.ToUpperInvariant(), sub, Color.FromRgb(0x7F, 0xC4, 0xFF), 84); }
        else { voz = "¡Empate!"; MostrarMensajeEmpuje("¡EMPATE!", sub, ColOro, 110); }

        if (_settings.UsarVoz) _voz.Decir(voz);
        _efectos.Reproducir("ganador", _settings.SonidoGanador);
        if (r.Winner != null) PulsarMarcador(r.Winner.Value);
    }

    private async Task OcultarMensajeTrasAsync(int ms)
    {
        await Task.Delay(ms);
        if (_push.State == GameState.RondaActiva) MostrarMensajeEmpuje("", "", Colors.White, 100);
    }

    private void MostrarMensajeEmpuje(string msg, string sub, Color color, double tamano)
    {
        TxtEmpujeMsg.Text = msg;
        TxtEmpujeMsg.FontSize = tamano;
        TxtEmpujeMsg.Foreground = new SolidColorBrush(color);
        TxtEmpujeSub.Text = sub;
    }

    private void TickEmpuje()
    {
        ActualizarRelojEmpuje();

        // la línea se desliza suavemente hacia su posición
        double dif = _bxObjetivo - _bx;
        if (Math.Abs(dif) > 0.05)
        {
            _bx += dif * 0.22;
            PosicionarEscena();
        }
    }

    /// <summary>Anillo y número del cronómetro: minutos restantes (o segundos en el último minuto).</summary>
    private void ActualizarRelojEmpuje()
    {
        double total = _push.DurationMs;
        double rest = _push.RemainingMs;
        RelojAnillo.Progress = total > 0 ? rest / total : 0;

        string num, uni;
        bool urgente = false;
        if (_push.State == GameState.RondaActiva)
        {
            long seg = (long)Math.Ceiling(rest / 1000.0);
            if (seg >= 60) { num = ((long)Math.Ceiling(seg / 60.0)).ToString(CultureInfo.InvariantCulture); uni = "min"; }
            else { num = seg.ToString(CultureInfo.InvariantCulture); uni = "s"; urgente = seg <= 10; }
        }
        else
        {
            num = _push.DurationMinutes.ToString(CultureInfo.InvariantCulture);
            uni = "min";
        }

        if (TxtTiempoNum.Text != num) TxtTiempoNum.Text = num;
        if (TxtTiempoUnidad.Text != uni) TxtTiempoUnidad.Text = uni;
        var color = urgente ? Brushes.OrangeRed : _brushVerdeReloj;
        if (!ReferenceEquals(TxtTiempoNum.Foreground, color))
        {
            TxtTiempoNum.Foreground = color;
            TxtTiempoUnidad.Foreground = color;
        }
    }

    private static readonly Brush _brushVerdeReloj = new SolidColorBrush(Color.FromRgb(0x7C, 0xFF, 0x2B));

    /// <summary>Coloca los dos fondos, el rayo y la explosión según la posición actual de la línea.</summary>
    private void PosicionarEscena()
    {
        TrRosa.X = _bx + MargenLinea - 1700;      // el rosa termina justo en la línea
        TrAzul.X = _bx - MargenLinea;             // el azul empieza justo en la línea
        TrExplosion.X = _bx - 160;

        var pts = new Point[Rayo.Length];
        for (int i = 0; i < Rayo.Length; i++) pts[i] = new Point(_bx + Rayo[i].dx, Rayo[i].fy * AltoD);

        var rayo = new StreamGeometry();
        using (var ctx = rayo.Open())
        {
            ctx.BeginFigure(pts[0], false, false);
            ctx.PolyLineTo(pts.Skip(1).ToList(), true, false);
        }
        rayo.Freeze();
        BoltPath.Data = rayo;

        var recorte = new StreamGeometry();
        using (var ctx = recorte.Open())
        {
            ctx.BeginFigure(pts[0], true, true);
            var lista = pts.Skip(1).ToList();
            lista.Add(new Point(AnchoD + 20, AltoD + 20));
            lista.Add(new Point(AnchoD + 20, -20));
            ctx.PolyLineTo(lista, true, false);
        }
        recorte.Freeze();
        CapaAzul.Clip = recorte;
    }

    private void CargarFondos()
    {
        ImgRosa.Source = CargarImagen(_settings.FondoRosaPath, "fondo_rosa.jpg");
        ImgAzul.Source = CargarImagen(_settings.FondoAzulPath, "fondo_azul.jpg");
    }

    private static ImageSource? CargarImagen(string? ruta, string recursoPorDefecto)
    {
        static BitmapImage Abrir(Uri uri)
        {
            var bmp = new BitmapImage();
            bmp.BeginInit();
            bmp.CacheOption = BitmapCacheOption.OnLoad;   // no deja el archivo bloqueado
            bmp.UriSource = uri;
            bmp.EndInit();
            bmp.Freeze();
            return bmp;
        }

        try
        {
            if (!string.IsNullOrWhiteSpace(ruta) && File.Exists(ruta)) return Abrir(new Uri(ruta));
        }
        catch { /* imagen dañada o ilegible: se usa la de fábrica */ }

        try { return Abrir(new Uri("pack://application:,,,/Assets/" + recursoPorDefecto)); }
        catch { return null; }
    }

    private void ConstruirFilasFondos()
    {
        PanelFondos.Children.Clear();
        _cfgFondoTxt.Clear();
        var estiloBtn = (Style)FindResource("ChipButton");

        foreach (var (slot, nombre, actual) in new[]
        {
            ("rosa", "Rojo (rosa)", _settings.FondoRosaPath),
            ("azul", "Azul", _settings.FondoAzulPath)
        })
        {
            _cfgFondos[slot] = actual;

            var fila = new Grid { Margin = new Thickness(0, 0, 0, 6) };
            fila.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(170) });
            fila.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            fila.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
            fila.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });

            var lbl = new TextBlock { Text = nombre, Foreground = Brushes.White, FontSize = 18, VerticalAlignment = VerticalAlignment.Center };
            var arch = new TextBlock
            {
                FontSize = 15,
                Foreground = new SolidColorBrush(Color.FromRgb(0xB8, 0xFF, 0x3F)),
                VerticalAlignment = VerticalAlignment.Center,
                TextTrimming = TextTrimming.CharacterEllipsis,
                Margin = new Thickness(0, 0, 8, 0)
            };
            _cfgFondoTxt[slot] = arch;
            ActualizarTextoFondo(slot);

            Button Boton(string txt, int col, double ancho, RoutedEventHandler h)
            {
                var b = new Button { Content = txt, Style = estiloBtn, Width = ancho, Height = 40, FontSize = 14, Margin = new Thickness(4, 0, 0, 0) };
                Grid.SetColumn(b, col);
                b.Click += h;
                return b;
            }

            Grid.SetColumn(lbl, 0);
            Grid.SetColumn(arch, 1);
            fila.Children.Add(lbl);
            fila.Children.Add(arch);
            fila.Children.Add(Boton("ELEGIR…", 2, 100, (_, _) => ElegirFondo(slot)));
            fila.Children.Add(Boton("DEFECTO", 3, 100, (_, _) => { _cfgFondos[slot] = ""; ActualizarTextoFondo(slot); }));
            PanelFondos.Children.Add(fila);
        }
    }

    private void ActualizarTextoFondo(string slot)
    {
        string v = _cfgFondos.GetValueOrDefault(slot, "");
        _cfgFondoTxt[slot].Text = string.IsNullOrWhiteSpace(v) ? "(el de fábrica)" : System.IO.Path.GetFileName(v);
    }

    private void ElegirFondo(string slot)
    {
        var dlg = new Microsoft.Win32.OpenFileDialog
        {
            Title = "Elegir imagen de fondo",
            Filter = "Imágenes (*.jpg;*.jpeg;*.png;*.bmp)|*.jpg;*.jpeg;*.png;*.bmp|Todos los archivos|*.*"
        };
        if (dlg.ShowDialog(this) == true)
        {
            _cfgFondos[slot] = dlg.FileName;
            ActualizarTextoFondo(slot);
        }
    }

    // ------------------------------------------------------------------
    //  Formatos
    // ------------------------------------------------------------------
    private static string FormatSeconds(double ms) =>
        Math.Min(ms / 1000.0, 99.99).ToString("00.00", CultureInfo.InvariantCulture);

    /// <summary>MM:SS.cc</summary>
    private static string FormatTime(double ms)
    {
        long cs = (long)(ms / 10.0);
        long m = Math.Min(cs / 6000, 99);
        long s = cs / 100 % 60;
        long c = cs % 100;
        return string.Format(CultureInfo.InvariantCulture, "{0:00}:{1:00}.{2:00}", m, s, c);
    }

    private string FormatTarget() =>
        string.Format(CultureInfo.InvariantCulture, "{0:00}:00", _target.TargetMinutes);

    private static string FormatKey(string k)
    {
        if (k.Length == 2 && k[0] == 'D' && char.IsDigit(k[1])) return k[1].ToString();
        if (k.StartsWith("NumPad", StringComparison.Ordinal) && k.Length > 6) return k.Substring(6);
        return k.ToUpperInvariant();
    }

    private static void PonerMarcaDeTecla(TextBlock tb, string tecla)
    {
        string t = FormatKey(tecla);
        tb.Text = t;
        tb.FontSize = t.Length == 1 ? 96 : t.Length <= 3 ? 56 : 28;
    }

    private void AplicarConfiguracion()
    {
        bool t = _modo == Modo.TiempoObjetivo;
        TxtTituloInicio.Text = _settings.TituloDesafio.ToUpperInvariant();
        PonerMarcaDeTecla(TxtKeyRojo, t ? "D1" : _settings.BotonRojo);
        PonerMarcaDeTecla(TxtKeyAzul, t ? "D2" : _settings.BotonAzul);
        TxtEmpujeAyuda.Text =
            $"← → tiempo · ESPACIO iniciar · {FormatKey(_settings.BotonRojo)} / {FormatKey(_settings.BotonAzul)} (o 1 / 2) empujar · clic izq. / der. · TAB modo";
    }

    // ------------------------------------------------------------------
    //  Teclado
    // ------------------------------------------------------------------
    private void Window_PreviewKeyDown(object sender, KeyEventArgs e)
    {
        Key key = e.Key == Key.System ? e.SystemKey : e.Key;

        // Con la configuración abierta no se juega
        if (PantallaConfig.Visibility == Visibility.Visible)
        {
            if (key == Key.Escape) { CerrarConfig(); e.Handled = true; }
            return;
        }

        if (PantallaInicio.Visibility == Visibility.Visible)
        {
            if (key == Key.Enter) { PantallaInicio.Visibility = Visibility.Collapsed; e.Handled = true; }
            else if (key == Key.F11) { if (!e.IsRepeat) ToggleFullscreen(); e.Handled = true; }
            return;
        }

        if (key == Key.F11 || (key == Key.Escape && _fullscreen))
        {
            if (!e.IsRepeat) ToggleFullscreen();
            e.Handled = true;
            return;
        }

        if (key == Key.F1)
        {
            if (!e.IsRepeat) AbrirConfig();
            e.Handled = true;
            return;
        }

        if (key == Key.Tab)
        {
            if (!e.IsRepeat) CambiarModo();
            e.Handled = true;
            return;
        }

        // Teclas propias de los modos Tiempo Objetivo y Empuje
        if (_modo != Modo.Reaccion)
        {
            if (key == Key.Left || key == Key.Right)
            {
                if (_modo == Modo.Empuje) _push.AdjustDuration(key == Key.Right ? 1 : -1);
                else _target.AdjustTarget(key == Key.Right ? 1 : -1);   // se permite mantener pulsada
                e.Handled = true;
                return;
            }
            if (key is Key.D1 or Key.NumPad1) { if (!e.IsRepeat) Presionar(Team.Rojo); e.Handled = true; return; }
            if (key is Key.D2 or Key.NumPad2) { if (!e.IsRepeat) Presionar(Team.Azul); e.Handled = true; return; }
        }

        string name = key.ToString();

        if (name == _settings.BotonRojo)
        {
            if (!e.IsRepeat) Presionar(Team.Rojo);
            e.Handled = true;
        }
        else if (name == _settings.BotonAzul)
        {
            if (!e.IsRepeat) Presionar(Team.Azul);
            e.Handled = true;
        }
        else if (name == _settings.BotonReinicio)
        {
            if (!e.IsRepeat) Reiniciar();
            e.Handled = true;
        }
        else if (key == Key.Space)
        {
            if (!e.IsRepeat) IniciarRonda();
            e.Handled = true;
        }
    }

    private void Window_PreviewKeyUp(object sender, KeyEventArgs e)
    {
        Key key = e.Key == Key.System ? e.SystemKey : e.Key;
        string name = key.ToString();
        if (name == _settings.BotonRojo || key is Key.D1 or Key.NumPad1) VisualBoton(Team.Rojo, false);
        if (name == _settings.BotonAzul || key is Key.D2 or Key.NumPad2) VisualBoton(Team.Azul, false);
    }

    private void ToggleFullscreen()
    {
        if (!_fullscreen)
        {
            WindowState = WindowState.Normal;
            WindowStyle = WindowStyle.None;
            ResizeMode = ResizeMode.NoResize;
            WindowState = WindowState.Maximized;
        }
        else
        {
            WindowStyle = WindowStyle.SingleBorderWindow;
            ResizeMode = ResizeMode.CanResize;
            WindowState = WindowState.Normal;
        }
        _fullscreen = !_fullscreen;
    }

    // ------------------------------------------------------------------
    //  Botones de la pantalla
    // ------------------------------------------------------------------
    private void BtnIniciar_Click(object sender, RoutedEventArgs e) => IniciarRonda();
    private void BtnReiniciar_Click(object sender, RoutedEventArgs e) => Reiniciar();
    private void BtnConfig_Click(object sender, RoutedEventArgs e) => AbrirConfig();
    private void BtnCerrarConfig_Click(object sender, RoutedEventArgs e) => CerrarConfig();
    private void BtnPantallaCompleta_Click(object sender, RoutedEventArgs e) => ToggleFullscreen();
    private void BtnTiempoMenos_Click(object sender, RoutedEventArgs e) => _push.AdjustDuration(-1);
    private void BtnTiempoMas_Click(object sender, RoutedEventArgs e) => _push.AdjustDuration(1);

    // Mouse: clic izquierdo en la mitad izquierda empuja el Rojo; en la mitad derecha, el Azul
    private void Empuje_MouseDown(object sender, MouseButtonEventArgs e)
    {
        double x = e.GetPosition(FondoEmpuje).X;
        Presionar(x < AnchoD / 2 ? Team.Rojo : Team.Azul);
    }
    // En el modo Tiempo Objetivo las flechas cambian el objetivo; en el otro modo vuelven al Tiempo Objetivo.
    private void ModoAnterior_Click(object sender, MouseButtonEventArgs e)
    {
        if (_modo == Modo.TiempoObjetivo) _target.AdjustTarget(-1); else CambiarModo();
    }

    private void ModoSiguiente_Click(object sender, MouseButtonEventArgs e)
    {
        if (_modo == Modo.TiempoObjetivo) _target.AdjustTarget(1); else CambiarModo();
    }

    private void PantallaInicio_MouseDown(object sender, MouseButtonEventArgs e) =>
        PantallaInicio.Visibility = Visibility.Collapsed;

    // ------------------------------------------------------------------
    //  Configuración
    // ------------------------------------------------------------------
    private void AbrirConfig()
    {
        TxtCfgTitulo.Text = _settings.TituloDesafio;
        TxtCfgLimite.Text = _settings.TiempoLimiteSegundos.ToString(CultureInfo.InvariantCulture);
        KeyRojo.Text = _settings.BotonRojo;
        KeyAzul.Text = _settings.BotonAzul;
        KeyReinicio.Text = _settings.BotonReinicio;
        _cfgMusica = _settings.MusicaPath;
        MostrarMusicaCfg();
        ChkVoz.IsChecked = _settings.UsarVoz;
        ChkPulsador.IsChecked = _settings.UsarPulsador;
        ConstruirFilasFondos();
        TxtCfgMargen.Text = _settings.MargenAciertoSegundos.ToString("0.##", CultureInfo.InvariantCulture);
        ConstruirFilasSonidos();
        TxtCfgAviso.Text = "";
        PantallaConfig.Visibility = Visibility.Visible;
    }

    private void MostrarMusicaCfg() =>
        TxtCfgMusica.Text = string.IsNullOrWhiteSpace(_cfgMusica) ? "(ninguna)" : System.IO.Path.GetFileName(_cfgMusica);

    private void CerrarConfig()
    {
        string titulo = TxtCfgTitulo.Text.Trim();
        if (titulo.Length > 0) _settings.TituloDesafio = titulo;

        if (int.TryParse(TxtCfgLimite.Text, NumberStyles.None, CultureInfo.InvariantCulture, out int lim))
            _settings.TiempoLimiteSegundos = Math.Clamp(lim, 3, 60);

        _settings.BotonRojo = KeyRojo.Text;
        _settings.BotonAzul = KeyAzul.Text;
        _settings.BotonReinicio = KeyReinicio.Text;
        _settings.MusicaPath = _cfgMusica;
        _settings.UsarVoz = ChkVoz.IsChecked == true;
        _settings.UsarPulsador = ChkPulsador.IsChecked == true;
        _settings.FondoRosaPath = _cfgFondos.GetValueOrDefault("rosa", "");
        _settings.FondoAzulPath = _cfgFondos.GetValueOrDefault("azul", "");
        if (double.TryParse(TxtCfgMargen.Text.Replace(',', '.'), NumberStyles.Float, CultureInfo.InvariantCulture, out double mg))
            _settings.MargenAciertoSegundos = mg;
        foreach (var (slot, _) in Slots) SetSonido(slot, _cfgSonidos.GetValueOrDefault(slot, ""));
        _settings.Normalize();
        _settings.Save();
        _target.MargenMs = _settings.MargenAciertoSegundos * 1000.0;

        AplicarConfiguracion();
        CargarFondos();
        PantallaConfig.Visibility = Visibility.Collapsed;
        Focus();
    }

    private string GetSonido(string slot) => slot switch
    {
        "cuenta" => _settings.SonidoCuenta,
        "ahora" => _settings.SonidoAhora,
        "detener" => _settings.SonidoDetener,
        _ => _settings.SonidoGanador
    };

    private void SetSonido(string slot, string valor)
    {
        switch (slot)
        {
            case "cuenta": _settings.SonidoCuenta = valor; break;
            case "ahora": _settings.SonidoAhora = valor; break;
            case "detener": _settings.SonidoDetener = valor; break;
            default: _settings.SonidoGanador = valor; break;
        }
    }

    private void ConstruirFilasSonidos()
    {
        PanelSonidos.Children.Clear();
        _cfgSonidoTxt.Clear();
        var estiloBtn = (Style)FindResource("ChipButton");

        foreach (var (slot, nombre) in Slots)
        {
            _cfgSonidos[slot] = GetSonido(slot);

            var fila = new Grid { Margin = new Thickness(0, 0, 0, 6) };
            fila.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(170) });
            fila.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            fila.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
            fila.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
            fila.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });

            var lbl = new TextBlock { Text = nombre, Foreground = Brushes.White, FontSize = 18, VerticalAlignment = VerticalAlignment.Center };
            var arch = new TextBlock
            {
                FontSize = 15,
                Foreground = new SolidColorBrush(Color.FromRgb(0xB8, 0xFF, 0x3F)),
                VerticalAlignment = VerticalAlignment.Center,
                TextTrimming = TextTrimming.CharacterEllipsis,
                Margin = new Thickness(0, 0, 8, 0)
            };
            _cfgSonidoTxt[slot] = arch;
            ActualizarTextoSonido(slot);

            Button Boton(string txt, int col, double ancho, RoutedEventHandler h)
            {
                var b = new Button { Content = txt, Style = estiloBtn, Width = ancho, Height = 40, FontSize = 14, Margin = new Thickness(4, 0, 0, 0) };
                Grid.SetColumn(b, col);
                b.Click += h;
                return b;
            }

            Grid.SetColumn(lbl, 0);
            Grid.SetColumn(arch, 1);
            fila.Children.Add(lbl);
            fila.Children.Add(arch);
            fila.Children.Add(Boton("▶", 2, 46, (_, _) => _efectos.Reproducir(slot, _cfgSonidos[slot])));
            fila.Children.Add(Boton("ELEGIR…", 3, 100, (_, _) => ElegirSonido(slot)));
            fila.Children.Add(Boton("DEFECTO", 4, 100, (_, _) => { _cfgSonidos[slot] = ""; ActualizarTextoSonido(slot); }));
            PanelSonidos.Children.Add(fila);
        }
    }

    private void ActualizarTextoSonido(string slot)
    {
        string v = _cfgSonidos.GetValueOrDefault(slot, "");
        _cfgSonidoTxt[slot].Text = string.IsNullOrWhiteSpace(v) ? "(por defecto)" : System.IO.Path.GetFileName(v);
    }

    private void ElegirSonido(string slot)
    {
        var dlg = new Microsoft.Win32.OpenFileDialog
        {
            Title = "Elegir sonido (MP3 o WAV)",
            Filter = "Audio (*.mp3;*.wav;*.wma;*.m4a)|*.mp3;*.wav;*.wma;*.m4a|Todos los archivos|*.*"
        };
        if (dlg.ShowDialog(this) == true)
        {
            _cfgSonidos[slot] = dlg.FileName;
            ActualizarTextoSonido(slot);
        }
    }

    private void BtnElegirMusica_Click(object sender, RoutedEventArgs e)
    {
        var dlg = new Microsoft.Win32.OpenFileDialog
        {
            Title = "Elegir música de fondo",
            Filter = "Audio (*.mp3;*.wav;*.wma;*.m4a)|*.mp3;*.wav;*.wma;*.m4a|Todos los archivos|*.*"
        };
        if (dlg.ShowDialog(this) == true)
        {
            _cfgMusica = dlg.FileName;
            MostrarMusicaCfg();
        }
    }

    private void BtnQuitarMusica_Click(object sender, RoutedEventArgs e)
    {
        _cfgMusica = "";
        MostrarMusicaCfg();
    }

    private void KeyBox_PreviewKeyDown(object sender, KeyEventArgs e)
    {
        e.Handled = true;
        var box = (TextBox)sender;
        Key key = e.Key == Key.System ? e.SystemKey : e.Key;

        if (Array.IndexOf(TeclasReservadas, key) >= 0)
        {
            TxtCfgAviso.Text = "Esa tecla está reservada (ESPACIO, ENTER, ESC, F1, F11, TAB, ← →). Elige otra.";
            return;
        }

        string name = key.ToString();
        foreach (var otra in new[] { KeyRojo, KeyAzul, KeyReinicio })
        {
            if (!ReferenceEquals(otra, box) && otra.Text == name)
            {
                TxtCfgAviso.Text = $"La tecla {FormatKey(name)} ya está asignada a otro botón.";
                return;
            }
        }

        box.Text = name;
        TxtCfgAviso.Text = "";
    }
}
