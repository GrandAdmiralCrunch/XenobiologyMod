using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace Xenobiology
{
    /// <summary>
    /// Field-guide portraits and silhouettes are only needed while the field guide is open, so they live under
    /// GameData/Xenobiology/PluginData (which KSP's GameDatabase does not load) and are read from disk the first time
    /// they are drawn. Config paths stay the same ("Xenobiology/Textures/Portraits/x"): a texture GameDatabase did load
    /// (e.g. from an add-on that still ships it under Textures) is used first.
    /// </summary>
    public static class XenoTextures
    {
        static readonly Dictionary<string, Texture2D> cache = new Dictionary<string, Texture2D>();

        public static Texture2D Get(string url)
        {
            if (string.IsNullOrEmpty(url)) return null;
            Texture2D t;
            if (cache.TryGetValue(url, out t)) return t;
            t = GameDatabase.Instance != null ? GameDatabase.Instance.GetTexture(url, false) : null;
            if (t == null)
            {
                string rel = url.Replace("/Textures/Silhouettes/", "/PluginData/Silhouettes/").Replace("/Textures/Portraits/", "/PluginData/Portraits/");
                string path = Path.Combine(KSPUtil.ApplicationRootPath, "GameData/" + rel + ".png");
                if (File.Exists(path))
                {
                    try
                    {
                        t = new Texture2D(2, 2, TextureFormat.RGBA32, false);
                        ImageConversion.LoadImage(t, File.ReadAllBytes(path), true);
                        t.wrapMode = TextureWrapMode.Clamp;
                        t.name = url;
                    }
                    catch (System.Exception e) { XenoLog.Warn("Could not load " + path + ": " + e.Message); t = null; }
                }
            }
            cache[url] = t;
            return t;
        }
    }
}
