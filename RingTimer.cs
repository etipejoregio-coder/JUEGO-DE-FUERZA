using System.Windows;
using System.Windows.Media;

namespace DesafioTiempoReaccion.Ui;

/// <summary>Anillo de 60 marcas: las verdes son el tiempo que queda, las pálidas el que ya pasó.</summary>
public class RingTimer : FrameworkElement
{
    private const int Marcas = 60;

    public static readonly DependencyProperty ProgressProperty = DependencyProperty.Register(
        nameof(Progress), typeof(double), typeof(RingTimer),
        new FrameworkPropertyMetadata(1.0, FrameworkPropertyMetadataOptions.AffectsRender));

    public static readonly DependencyProperty OnBrushProperty = DependencyProperty.Register(
        nameof(OnBrush), typeof(Brush), typeof(RingTimer),
        new FrameworkPropertyMetadata(Brushes.LimeGreen, FrameworkPropertyMetadataOptions.AffectsRender));

    public static readonly DependencyProperty OffBrushProperty = DependencyProperty.Register(
        nameof(OffBrush), typeof(Brush), typeof(RingTimer),
        new FrameworkPropertyMetadata(Brushes.Gainsboro, FrameworkPropertyMetadataOptions.AffectsRender));

    /// <summary>Fracción de tiempo restante (1 = todo, 0 = nada).</summary>
    public double Progress { get => (double)GetValue(ProgressProperty); set => SetValue(ProgressProperty, value); }
    public Brush OnBrush { get => (Brush)GetValue(OnBrushProperty); set => SetValue(OnBrushProperty, value); }
    public Brush OffBrush { get => (Brush)GetValue(OffBrushProperty); set => SetValue(OffBrushProperty, value); }

    protected override void OnRender(DrawingContext dc)
    {
        double w = ActualWidth, h = ActualHeight;
        if (w <= 0 || h <= 0) return;

        double R = Math.Min(w, h) / 2;
        var c = new Point(w / 2, h / 2);
        double r1 = R * 0.70, r2 = R * 0.98;
        int encendidas = (int)Math.Round(Math.Clamp(Progress, 0.0, 1.0) * Marcas);

        var penOn = new Pen(OnBrush, R * 0.075) { StartLineCap = PenLineCap.Round, EndLineCap = PenLineCap.Round };
        var penOff = new Pen(OffBrush, R * 0.075) { StartLineCap = PenLineCap.Round, EndLineCap = PenLineCap.Round };

        for (int i = 0; i < Marcas; i++)
        {
            double a = (-90 + i * 360.0 / Marcas) * Math.PI / 180.0;
            double cos = Math.Cos(a), sin = Math.Sin(a);
            dc.DrawLine(i < encendidas ? penOn : penOff,
                        new Point(c.X + cos * r1, c.Y + sin * r1),
                        new Point(c.X + cos * r2, c.Y + sin * r2));
        }
    }
}
