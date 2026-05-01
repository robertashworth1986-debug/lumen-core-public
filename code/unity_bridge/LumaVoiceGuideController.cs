using System;
using System.Collections;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;

[Serializable]
public class GuideRequest {
    public string prompt;
    public string mode;
}

[Serializable]
public class GuideResponse {
    public string generated_utc;
    public string mode;
    public string response;
    public int history_size;
}

public class LumaVoiceGuideController : MonoBehaviour {
    [SerializeField] private string baseUrl = "http://127.0.0.1:8787";

    public event Action<GuideResponse> OnGuideResponse;
    public event Action<string> OnGuideError;

    public void RequestConciergeBrief() {
        RequestGuide("brief", "concierge");
    }

    public void RequestAnalystBrief() {
        RequestGuide("brief", "analyst");
    }

    public void RequestPitchBrief() {
        RequestGuide("brief", "pitch");
    }

    public void RequestGuide(string prompt, string mode) {
        StartCoroutine(PostGuide(prompt, mode));
    }

    private IEnumerator PostGuide(string prompt, string mode) {
        var reqObj = new GuideRequest { prompt = prompt, mode = mode };
        var json = JsonUtility.ToJson(reqObj);
        var url = baseUrl.TrimEnd('/') + "/api/guide/respond";

        using var req = new UnityWebRequest(url, "POST");
        req.uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(json));
        req.downloadHandler = new DownloadHandlerBuffer();
        req.SetRequestHeader("Content-Type", "application/json");

        yield return req.SendWebRequest();

        if (req.result == UnityWebRequest.Result.Success) {
            try {
                var response = JsonUtility.FromJson<GuideResponse>(req.downloadHandler.text);
                OnGuideResponse?.Invoke(response);
            } catch (Exception ex) {
                OnGuideError?.Invoke(ex.Message);
            }
        } else {
            OnGuideError?.Invoke(req.error ?? "guide_request_failed");
        }
    }
}
