using System;
using System.Collections;
using UnityEngine;
using UnityEngine.Networking;

[Serializable]
public class LiveTruthGeometry
{
    public float curvature;
    public float resonance;
    public float persistence;
    public float scout_phase;
}

[Serializable]
public class LiveTruthPayload
{
    public string generated_utc;
    public string mode;
    public float lattice_score;
    public LiveTruthGeometry geometry;
}

public class LumaLiveTruthBridge : MonoBehaviour
{
    [Header("Gateway")]
    public string endpoint = "http://127.0.0.1:8787/api/live-truth/fabric";
    public float pollSeconds = 3f;

    [Header("Targets")]
    public Light sceneLight;
    public Renderer targetRenderer;

    private Material _material;

    private void Start()
    {
        if (targetRenderer != null)
        {
            _material = targetRenderer.material;
        }
        StartCoroutine(PollLoop());
    }

    private IEnumerator PollLoop()
    {
        while (true)
        {
            yield return FetchAndApply();
            yield return new WaitForSeconds(Mathf.Max(1f, pollSeconds));
        }
    }

    private IEnumerator FetchAndApply()
    {
        using (UnityWebRequest req = UnityWebRequest.Get(endpoint))
        {
            yield return req.SendWebRequest();
            if (req.result != UnityWebRequest.Result.Success)
            {
                yield break;
            }

            var json = req.downloadHandler.text;
            if (string.IsNullOrWhiteSpace(json))
            {
                yield break;
            }

            LiveTruthPayload payload = null;
            try
            {
                payload = JsonUtility.FromJson<LiveTruthPayload>(json);
            }
            catch
            {
                yield break;
            }

            if (payload == null)
            {
                yield break;
            }

            ApplyPayload(payload);
        }
    }

    private void ApplyPayload(LiveTruthPayload payload)
    {
        float score = Mathf.Clamp01(payload.lattice_score);
        float curvature = payload.geometry != null ? Mathf.Clamp01(payload.geometry.curvature) : score;
        float resonance = payload.geometry != null ? Mathf.Clamp01(payload.geometry.resonance) : score;

        if (sceneLight != null)
        {
            sceneLight.intensity = Mathf.Lerp(0.9f, 2.4f, score);
            sceneLight.color = Color.Lerp(new Color(0.32f, 0.78f, 1f), new Color(0.15f, 1f, 0.74f), resonance);
        }

        if (_material != null)
        {
            Color c = Color.Lerp(new Color(0.1f, 0.22f, 0.45f), new Color(0.3f, 0.95f, 0.75f), curvature);
            _material.SetColor("_EmissionColor", c * Mathf.Lerp(0.2f, 1.8f, score));
        }
    }
}
