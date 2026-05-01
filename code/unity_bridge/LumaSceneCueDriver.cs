using UnityEngine;

public class LumaSceneCueDriver : MonoBehaviour {
    [SerializeField] private LumaWsClientBridge wsBridge;
    [SerializeField] private Light pulseLight;
    [SerializeField] private Renderer coreRenderer;
    [SerializeField] private Color calmColor = new Color(0.35f, 0.95f, 0.84f);
    [SerializeField] private Color warningColor = new Color(1f, 0.35f, 0.35f);

    private void Awake() {
        if (wsBridge == null) {
            wsBridge = FindObjectOfType<LumaWsClientBridge>();
        }
    }

    private void OnEnable() {
        if (wsBridge == null) return;
        wsBridge.OnSceneCueMessage += HandleCue;
    }

    private void OnDisable() {
        if (wsBridge == null) return;
        wsBridge.OnSceneCueMessage -= HandleCue;
    }

    private void HandleCue(string payload) {
        bool warning = payload.Contains("warning") || payload.Contains("loss") || payload.Contains("critical");
        float intensity = ExtractIntensity(payload);
        Color c = warning ? warningColor : calmColor;

        if (pulseLight != null) {
            pulseLight.color = c;
            pulseLight.intensity = Mathf.Lerp(0.9f, 4.2f, intensity);
        }

        if (coreRenderer != null && coreRenderer.material != null) {
            coreRenderer.material.EnableKeyword("_EMISSION");
            coreRenderer.material.SetColor("_EmissionColor", c * Mathf.Lerp(0.5f, 2.5f, intensity));
        }
    }

    private float ExtractIntensity(string payload) {
        const string token = "\"intensity\":";
        int idx = payload.IndexOf(token);
        if (idx < 0) return 0.5f;
        int start = idx + token.Length;
        int end = start;
        while (end < payload.Length && "0123456789.-".IndexOf(payload[end]) >= 0) {
            end += 1;
        }

        if (float.TryParse(payload.Substring(start, end - start), out float value)) {
            return Mathf.Clamp01(value);
        }

        return 0.5f;
    }
}
