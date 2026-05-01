#if UNITY_EDITOR
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

public static class LumaExperienceAutoRigEditor {
    [MenuItem("Tools/LumaCore/Build Experience Rig")]
    public static void BuildExperienceRig() {
        var root = new GameObject("LumaExperienceRoot");

        var bridgeGO = new GameObject("LumaRealtimeBridge");
        bridgeGO.transform.SetParent(root.transform);
        bridgeGO.AddComponent<LumaRealtimeBridge>();

        var wsGO = new GameObject("LumaWsClientBridge");
        wsGO.transform.SetParent(root.transform);
        wsGO.AddComponent<LumaWsClientBridge>();

        var voiceGO = new GameObject("LumaVoiceGuideController");
        voiceGO.transform.SetParent(root.transform);
        voiceGO.AddComponent<LumaVoiceGuideController>();

        var cueGO = new GameObject("LumaSceneCueDriver");
        cueGO.transform.SetParent(root.transform);
        var cueDriver = cueGO.AddComponent<LumaSceneCueDriver>();

        var core = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        core.name = "LumaCoreSphere";
        core.transform.SetParent(root.transform);
        core.transform.position = new Vector3(0f, 1.2f, 0f);
        core.transform.localScale = new Vector3(2.5f, 2.5f, 2.5f);

        var coreRenderer = core.GetComponent<Renderer>();
        if (coreRenderer != null) {
            var mat = new Material(Shader.Find("Universal Render Pipeline/Lit"));
            mat.color = new Color(0.35f, 0.95f, 0.84f, 0.9f);
            mat.EnableKeyword("_EMISSION");
            mat.SetColor("_EmissionColor", new Color(0.18f, 0.9f, 0.8f, 1f));
            coreRenderer.sharedMaterial = mat;
        }

        var lightGO = new GameObject("LumaPulseLight");
        lightGO.transform.SetParent(root.transform);
        lightGO.transform.position = new Vector3(0f, 2.8f, 1.2f);
        var pulseLight = lightGO.AddComponent<Light>();
        pulseLight.type = LightType.Point;
        pulseLight.intensity = 2.0f;
        pulseLight.range = 18.0f;
        pulseLight.color = new Color(0.35f, 0.95f, 0.84f);
        pulseLight.shadows = LightShadows.Soft;

        var camera = Camera.main;
        if (camera == null) {
            var camGO = new GameObject("Main Camera");
            camGO.tag = "MainCamera";
            camera = camGO.AddComponent<Camera>();
            camGO.AddComponent<AudioListener>();
        }

        camera.transform.position = new Vector3(0f, 1.7f, -7f);
        camera.transform.rotation = Quaternion.Euler(8f, 0f, 0f);
        camera.clearFlags = CameraClearFlags.SolidColor;
        camera.backgroundColor = new Color(0.02f, 0.05f, 0.09f);

        var directionalGO = new GameObject("Directional Light");
        directionalGO.transform.SetParent(root.transform);
        directionalGO.transform.rotation = Quaternion.Euler(50f, -30f, 0f);
        var directional = directionalGO.AddComponent<Light>();
        directional.type = LightType.Directional;
        directional.intensity = 0.35f;

        // Wire references by serialized-object editing to avoid requiring public setters.
        var so = new SerializedObject(cueDriver);
        so.FindProperty("wsBridge").objectReferenceValue = wsGO.GetComponent<LumaWsClientBridge>();
        so.FindProperty("pulseLight").objectReferenceValue = pulseLight;
        so.FindProperty("coreRenderer").objectReferenceValue = coreRenderer;
        so.ApplyModifiedPropertiesWithoutUndo();

        EditorSceneManager.MarkAllScenesDirty();
        Selection.activeGameObject = root;
        Debug.Log("Luma experience rig created. Press Play to connect to gateway at http://127.0.0.1:8787.");
    }
}
#endif
