using Godot;

namespace StS2Tracker;

/// <summary>
/// In-game overlay showing the web dashboard URL in the top-right corner.
/// </summary>
public partial class StatusOverlay : CanvasLayer
{
    private static StatusOverlay? _instance;
    private Label? _label;

    public static void Create(int port)
    {
        if (_instance != null) return;

        _instance = new StatusOverlay();
        _instance.Layer = 100;
        _instance.Name = "StS2TrackerOverlay";

        var label = new Label();
        label.Text = $"STS Tracker: http://localhost:{port}";
        label.HorizontalAlignment = HorizontalAlignment.Right;
        label.VerticalAlignment = VerticalAlignment.Top;

        // Top-right corner
        label.AnchorLeft = 1.0f;
        label.AnchorRight = 1.0f;
        label.AnchorTop = 0.0f;
        label.AnchorBottom = 0.0f;
        label.OffsetLeft = -670;
        label.OffsetRight = -360;
        label.OffsetTop = 10;
        label.OffsetBottom = 50;
        label.GrowHorizontal = Control.GrowDirection.Begin;

        // Semi-transparent green text
        label.AddThemeColorOverride("font_color", new Color(0.6f, 0.9f, 0.6f, 0.8f));
        label.AddThemeFontSizeOverride("font_size", 14);

        _instance._label = label;
        _instance.AddChild(label);

        var tree = Engine.GetMainLoop() as SceneTree;
        tree?.Root.CallDeferred("add_child", _instance);

        ModEntry.Log("Status overlay created");
    }

    public static void UpdateStatus(string text)
    {
        if (_instance?._label != null)
            _instance._label.Text = text;
    }
}
