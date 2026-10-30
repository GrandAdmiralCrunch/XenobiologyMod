using System;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using UnityEngine;

namespace Xenobiology
{
    /// <summary>
    /// Soft link to MicrobiologyExpansion. No compile-time reference: the bridge finds the mod's
    /// MicrobiologyDatabase by reflection and reads which microbes the save has discovered and
    /// lab-processed. Without the mod every query simply answers "no".
    /// </summary>
    public static class MicrobeBridge
    {
        static bool searched;
        static Type dbType;
        static PropertyInfo pInstance, pDiscovered;
        static MethodInfo mProcessed;
        static FieldInfo fName;

        static readonly HashSet<string> discovered = new HashSet<string>();
        static readonly HashSet<string> processed = new HashSet<string>();
        static float nextPoll;
        static int stamp;

        public static bool Installed { get { Find(); return dbType != null; } }

        /// <summary>Changes whenever the set of discovered / processed microbes changes.</summary>
        public static int Stamp { get { Poll(false); return stamp; } }

        public static bool IsDiscovered(string microbe) { Poll(false); return microbe != null && discovered.Contains(microbe); }
        public static bool IsProcessed(string microbe) { Poll(false); return microbe != null && processed.Contains(microbe); }
        public static bool IsDiscovered(MicrobeDef m) { return m != null && IsDiscovered(m.name); }
        public static bool IsProcessed(MicrobeDef m) { return m != null && IsProcessed(m.name); }

        static void Find()
        {
            if (searched) return;
            searched = true;
            try
            {
                foreach (AssemblyLoader.LoadedAssembly la in AssemblyLoader.loadedAssemblies)
                {
                    if (la.assembly == null || la.name == null || !la.name.StartsWith("MicrobiologyExpansion", StringComparison.OrdinalIgnoreCase)) continue;
                    dbType = la.assembly.GetType("MicrobiologyDatabase");
                    if (dbType != null) break;
                }
                if (dbType == null) { XenoLog.Info("MicrobiologyExpansion not installed; microbe leaves disabled"); return; }
                const BindingFlags F = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static;
                pInstance = dbType.GetProperty("Instance", F);
                pDiscovered = dbType.GetProperty("DiscoveredMicrobes", F);
                mProcessed = dbType.GetMethod("IsMicrobeProcessed", F);
                Type microbe = dbType.Assembly.GetType("Microbe");
                if (microbe != null) fName = microbe.GetField("name", F);
                if (pInstance == null || pDiscovered == null || fName == null)
                {
                    XenoLog.Warn("MicrobiologyExpansion found but its API has changed; microbe discovery will not be tracked");
                    dbType = null;
                    return;
                }
                XenoLog.Info("MicrobiologyExpansion bridge ready" + (mProcessed == null ? " (no lab-processing state)" : ""));
            }
            catch (Exception e) { XenoLog.Warn("MicrobiologyExpansion bridge failed: " + e.Message); dbType = null; }
        }

        /// <summary>Re-reads discovery state at most every 2 s (or now, if forced). Returns true if it changed.</summary>
        public static bool Poll(bool force)
        {
            Find();
            if (dbType == null) return false;
            if (!force && Time.realtimeSinceStartup < nextPoll) return false;
            nextPoll = Time.realtimeSinceStartup + 2f;
            try
            {
                object db = pInstance.GetValue(null, null);
                if (db == null) return false;
                var newDisc = new HashSet<string>();
                var newProc = new HashSet<string>();
                var disc = pDiscovered.GetValue(db, null) as IEnumerable;
                if (disc != null)
                    foreach (object m in disc)
                    {
                        string n = m != null ? fName.GetValue(m) as string : null;
                        if (n == null) continue;
                        newDisc.Add(n);
                        if (mProcessed != null && (bool)mProcessed.Invoke(db, new[] { m })) newProc.Add(n);
                    }
                bool changed = !newDisc.SetEquals(discovered) || !newProc.SetEquals(processed);
                if (changed)
                {
                    discovered.Clear(); discovered.UnionWith(newDisc);
                    processed.Clear(); processed.UnionWith(newProc);
                    stamp++;
                }
                return changed;
            }
            catch (Exception e) { XenoLog.Warn("MicrobiologyExpansion poll failed: " + e.Message); nextPoll = Time.realtimeSinceStartup + 30f; return false; }
        }

        /// <summary>Evidence a microbe contributes to its clade: 1 when discovered, +1 once lab-processed.</summary>
        public static int Evidence(MicrobeDef m)
        {
            if (!IsDiscovered(m)) return 0;
            return IsProcessed(m) ? 2 : 1;
        }
    }
}
