using System.Diagnostics;
namespace DesafioTiempoReaccion.GameEngine;

public class PushResult
{
    public int EmpujesRojo { get; init; }
    public int EmpujesAzul { get; init; }
    /// <summary>Equipo que empujó más; null si hubo empate.</summary>
    public Team? Winner { get; init; }
}

/// <summary>
/// Modo "Empuje" (tira y afloja): durante el tiempo elegido cada pulsación empuja la línea hacia el rival.
/// Al terminar el tiempo gana el equipo que empujó más. Debe usarse desde el hilo de la interfaz.
/// </summary>
public class PushEngine
{
    public const int MinMinutes = 5, MaxMinutes = 95, StepMinutes = 5;

    private CancellationTokenSource? _cts;
    private long _startTs;

    public GameState State { get; private set; } = GameState.Inicio;
    public int DurationMinutes { get; private set; } = MinMinutes;
    public double DurationMs => DurationMinutes * 60000.0;
    public int PuntosRojo { get; private set; }
    public int PuntosAzul { get; private set; }
    public int EmpujesRojo { get; private set; }
    public int EmpujesAzul { get; private set; }

    /// <summary>Empuje neto: positivo = va ganando el Rojo, negativo = va ganando el Azul.</summary>
    public int Net => EmpujesRojo - EmpujesAzul;

    public double ElapsedMs =>
        State == GameState.RondaActiva ? TicksToMs(Stopwatch.GetTimestamp() - _startTs) : 0;

    public double RemainingMs =>
        State == GameState.RondaActiva ? Math.Max(0, DurationMs - ElapsedMs) : DurationMs;

    public event Action<GameState>? StateChanged;
    public event Action<int>? CountdownTick;          // 3, 2, 1 y 0 (= ¡Ahora!)
    public event Action<Team>? Pushed;
    public event Action<PushResult>? Finished;
    public event Action? DurationChanged;

    public bool AdjustDuration(int steps)
    {
        if (State != GameState.Inicio && State != GameState.Ganador) return false;
        int nuevo = Math.Clamp(DurationMinutes + steps * StepMinutes, MinMinutes, MaxMinutes);
        if (nuevo == DurationMinutes) return false;
        DurationMinutes = nuevo;
        DurationChanged?.Invoke();
        return true;
    }

    public async Task StartAsync()
    {
        if (State != GameState.Inicio && State != GameState.Ganador) return;

        _cts?.Cancel();
        var cts = _cts = new CancellationTokenSource();
        var ct = cts.Token;
        EmpujesRojo = EmpujesAzul = 0;

        try
        {
            SetState(GameState.CuentaRegresiva);
            for (int n = 3; n >= 1; n--)
            {
                CountdownTick?.Invoke(n);
                await Task.Delay(1000, ct);
                ct.ThrowIfCancellationRequested();
            }

            _startTs = Stopwatch.GetTimestamp();
            SetState(GameState.RondaActiva);
            CountdownTick?.Invoke(0);

            await Task.Delay((int)Math.Min(DurationMs, int.MaxValue - 1), ct);
            ct.ThrowIfCancellationRequested();
            Finish();
        }
        catch (OperationCanceledException) { }
    }

    public void Push(Team team)
    {
        if (State != GameState.RondaActiva) return;
        if (team == Team.Rojo) EmpujesRojo++; else EmpujesAzul++;
        Pushed?.Invoke(team);
    }

    public void ResetGame()
    {
        _cts?.Cancel();
        PuntosRojo = PuntosAzul = 0;
        EmpujesRojo = EmpujesAzul = 0;
        SetState(GameState.Inicio);
    }

    private void Finish()
    {
        Team? winner = Net > 0 ? Team.Rojo : (Net < 0 ? Team.Azul : (Team?)null);
        if (winner == Team.Rojo) PuntosRojo++;
        else if (winner == Team.Azul) PuntosAzul++;

        SetState(GameState.Ganador);
        Finished?.Invoke(new PushResult { EmpujesRojo = EmpujesRojo, EmpujesAzul = EmpujesAzul, Winner = winner });
    }

    private static double TicksToMs(long ticks) => ticks * 1000.0 / Stopwatch.Frequency;

    private void SetState(GameState s)
    {
        State = s;
        StateChanged?.Invoke(s);
    }
}
