using System;
using UnityEngine;

namespace Xenobiology
{
    /// <summary>
    /// Global tunables, read from any XENOBIOLOGY_SETTINGS node (last one wins, so
    /// ModuleManager patches or user overrides work as expected).
    /// </summary>
    public static class XenoSettings
    {
        // Population
        public static int MaxActiveCreatures = 30;
        public static int MaxCreatureObjects = 60;        // hard limit on creature objects (herds and schools count 1/4 against MaxActiveCreatures)
        public static float SpawnRadius = 1200f;          // creatures appear inside this ring...
        public static float MinSpawnDistance = 150f;      // ...but not closer than this to the observer
        public static float DespawnRadius = 2000f;
        public static float MaxObserverAltitude = 4000f;  // above terrain; higher = no simulation
        public static float DensityMultiplier = 1f;
        public static float SpawnCheckInterval = 1.5f;
        public static float TerritoryCellKm = 3f;         // size of a deterministic "territory" cell

        // Fossils
        public static int MaxFossilSites = 6;
        public static float FossilSpawnRadius = 900f;
        public static float FossilDensity = 1f;

        // Interaction
        public static float DefaultObserveRange = 40f;
        public static float FossilStudyRange = 6f;
        public static KeyCode ObserveKey = KeyCode.O;
        public static KeyCode FieldGuideKey = KeyCode.None;
        public static KeyCode DebugKey = KeyCode.F8;       // used with Alt
        public static KeyCode MountKey = KeyCode.Y;        // mount / dismount a rideable creature
        public static KeyCode RideAttackKey = KeyCode.T;   // rider-triggered attack (e.g. tail swing)
        public static bool RequireRecoveryForScience = true;

        // Field guide
        public static bool SpoilerFree = true;            // hide biospheres with no discoveries
        public static bool ShowUndiscoveredSilhouettes = true;

        // Megafauna
        public static bool ProjectileDamage = true;      // thrown boulders can break parts (and hurt kerbals)
        public static bool LairWaypoints = true;         // mark discovered lairs with a waypoint

        // Performance (level of detail by distance from the camera; see CreatureLod.cs)
        public static bool LodEnabled = true;
        public static float LodNearDistance = 150f;      // + 10 m per metre of creature size: full detail inside this
        public static float LodFarDistance = 450f;       // + 25 m per metre: beyond this, motion runs every 3rd frame
        public static float LodCullDistance = 150f;      // + LodCullPerMetre per metre: beyond this the creature is hidden
        public static float LodCullPerMetre = 120f;
        public static bool CreatureShadows = true;       // near creatures cast shadows...
        public static float ShadowMinSize = 1.2f;        // ...if at least this long (small ones never do)
        public static bool KerbalDiving = true;          // EVA kerbals can dive below the surface (hold jetpack-down) and rise (jetpack-up)
        public static float LairLightRange = 250f;       // lair lights switch on only when the vessel is this close

        public static bool DebugMode = false;

        public static void Load()
        {
            ConfigNode[] nodes = GameDatabase.Instance.GetConfigNodes("XENOBIOLOGY_SETTINGS");
            if (nodes == null || nodes.Length == 0) return;
            ConfigNode n = nodes[nodes.Length - 1];

            n.TryGetValue("maxActiveCreatures", ref MaxActiveCreatures);
            n.TryGetValue("maxCreatureObjects", ref MaxCreatureObjects);
            n.TryGetValue("spawnRadius", ref SpawnRadius);
            n.TryGetValue("minSpawnDistance", ref MinSpawnDistance);
            n.TryGetValue("despawnRadius", ref DespawnRadius);
            n.TryGetValue("maxObserverAltitude", ref MaxObserverAltitude);
            n.TryGetValue("densityMultiplier", ref DensityMultiplier);
            n.TryGetValue("spawnCheckInterval", ref SpawnCheckInterval);
            n.TryGetValue("territoryCellKm", ref TerritoryCellKm);
            n.TryGetValue("maxFossilSites", ref MaxFossilSites);
            n.TryGetValue("fossilSpawnRadius", ref FossilSpawnRadius);
            n.TryGetValue("fossilDensity", ref FossilDensity);
            n.TryGetValue("defaultObserveRange", ref DefaultObserveRange);
            n.TryGetValue("fossilStudyRange", ref FossilStudyRange);
            n.TryGetValue("requireRecoveryForScience", ref RequireRecoveryForScience);
            n.TryGetValue("spoilerFree", ref SpoilerFree);
            n.TryGetValue("showUndiscoveredSilhouettes", ref ShowUndiscoveredSilhouettes);
            n.TryGetValue("debugMode", ref DebugMode);
            n.TryGetValue("lodEnabled", ref LodEnabled);
            n.TryGetValue("lodNearDistance", ref LodNearDistance);
            n.TryGetValue("lodFarDistance", ref LodFarDistance);
            n.TryGetValue("lodCullDistance", ref LodCullDistance);
            n.TryGetValue("lodCullPerMetre", ref LodCullPerMetre);
            n.TryGetValue("creatureShadows", ref CreatureShadows);
            n.TryGetValue("shadowMinSize", ref ShadowMinSize);
            n.TryGetValue("lairLightRange", ref LairLightRange);
            n.TryGetValue("kerbalDiving", ref KerbalDiving);
            n.TryGetValue("projectileDamage", ref ProjectileDamage);
            n.TryGetValue("lairWaypoints", ref LairWaypoints);

            ObserveKey = ParseKey(n.GetValue("observeKey"), ObserveKey);
            FieldGuideKey = ParseKey(n.GetValue("fieldGuideKey"), FieldGuideKey);
            DebugKey = ParseKey(n.GetValue("debugKey"), DebugKey);
            MountKey = ParseKey(n.GetValue("mountKey"), MountKey);
            RideAttackKey = ParseKey(n.GetValue("rideAttackKey"), RideAttackKey);

            if (DespawnRadius < SpawnRadius + 100f) DespawnRadius = SpawnRadius + 100f;
            XenoLog.Info("Settings loaded (maxActive=" + MaxActiveCreatures + ", spawnRadius=" + SpawnRadius + ")");
        }

        static KeyCode ParseKey(string s, KeyCode fallback)
        {
            if (string.IsNullOrEmpty(s)) return fallback;
            try { return (KeyCode)Enum.Parse(typeof(KeyCode), s.Trim(), true); }
            catch { XenoLog.Warn("Unknown key '" + s + "', using " + fallback); return fallback; }
        }
    }

    public static class XenoLog
    {
        public static void Info(string m) { Debug.Log("[Xenobiology] " + m); }
        public static void Warn(string m) { Debug.LogWarning("[Xenobiology] " + m); }
        public static void Error(string m) { Debug.LogError("[Xenobiology] " + m); }
        public static void Dbg(string m) { if (XenoSettings.DebugMode) Debug.Log("[Xenobiology:dbg] " + m); }
    }
}
