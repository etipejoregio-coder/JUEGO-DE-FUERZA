using System.IO;
using System.Text.Json;
namespace DesafioTiempoReaccion.GameEngine;

public class GameSettings
{
    public string TituloDesafio { get; set; } = "TIEMPO DE REACCIÓN";
    public int TiempoLimiteSegundos { get; set; } = 10;   // tiempo máximo para presionar tras la señal
    public string BotonRojo { get; set; } = "A";
    public string BotonAzul { get; set; } = "L";
    public string BotonReinicio { get; set; } = "R";
    public double MargenAciertoSegundos { get; set; } = 1.0;   // ± segundos para acertar el objetivo
    public bool UsarPulsador { get; set; } = false;   // pulsadores arcade USB (encoder): antirrebote
    public string FondoRosaPath { get; set; } = "";   // fondo del equipo Rojo/rosa (vacío = el de fábrica)
    public string FondoAzulPath { get; set; } = "";   // fondo del equipo Azul
    public bool UsarVoz { get; set; } = true;
    public string SonidoCuenta { get; set; } = "";    // vacío = sonido por defecto
    public string SonidoAhora { get; set; } = "";
    public string SonidoDetener { get; set; } = "";
    public string SonidoGanador { get; set; } = "";
    public string MusicaPath { get; set; } = "";   // MP3 de fondo (modo Tiempo Objetivo)

    public int CuentaRegresivaMs { get; set; } = 1500;
    public int EsperaMinMs { get; set; } = 2000;
    public int EsperaMaxMs { get; set; } = 5000;

    private static string FilePath => System.IO.Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
        "DesafioTiempoReaccion", "settings.json");

    public static GameSettings Load()
    {
        try
        {
            if (File.Exists(FilePath))
            {
                var s = JsonSerializer.Deserialize<GameSettings>(File.ReadAllText(FilePath));
                if (s != null) { s.Normalize(); return s; }
            }
        }
        catch { /* archivo dañado: se usan los valores por defecto */ }
        return new GameSettings();
    }

    public void Save()
    {
        try
        {
            Directory.CreateDirectory(System.IO.Path.GetDirectoryName(FilePath)!);
            File.WriteAllText(FilePath, JsonSerializer.Serialize(this, new JsonSerializerOptions { WriteIndented = true }));
        }
        catch { /* sin permisos de escritura: se ignora */ }
    }

    public void Normalize()
    {
        MargenAciertoSegundos = Math.Clamp(MargenAciertoSegundos, 0.05, 30.0);
        FondoRosaPath ??= ""; FondoAzulPath ??= "";
        MusicaPath ??= ""; SonidoCuenta ??= ""; SonidoAhora ??= ""; SonidoDetener ??= ""; SonidoGanador ??= "";
        if (string.IsNullOrWhiteSpace(TituloDesafio)) TituloDesafio = "TIEMPO DE REACCIÓN";
        TiempoLimiteSegundos = Math.Clamp(TiempoLimiteSegundos, 3, 60);
        if (string.IsNullOrWhiteSpace(BotonRojo)) BotonRojo = "A";
        if (string.IsNullOrWhiteSpace(BotonAzul)) BotonAzul = "L";
        if (string.IsNullOrWhiteSpace(BotonReinicio)) BotonReinicio = "R";
        if (CuentaRegresivaMs < 0) CuentaRegresivaMs = 1500;
        if (EsperaMinMs < 0 || EsperaMaxMs < EsperaMinMs) { EsperaMinMs = 2000; EsperaMaxMs = 5000; }
    }
}
