using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace Xenobiology
{
    /// <summary>
    /// Xenobiology analysis bench, added to science labs by ModuleManager. Scientists in the lab work through the
    /// specimens held in CO-Z units and the fossil samples (Palaeontological Survey data) carried anywhere on the
    /// vessel. Each finished analysis is worth science of its own and counts as +1 evidence for that lineage in the
    /// tree of life, once per species or fossil type.
    /// </summary>
    public class ModuleXenoAnalysis : PartModule
    {
        [KSPField] public float hoursPerItem = 3f;            // game hours (6 h days) for one analysis by one level-0 scientist
        [KSPField] public float ecPerSecond = 1.5f;
        [KSPField] public float specimenMultiplier = 2f;      // science = scienceValue x this
        [KSPField] public float fossilMultiplier = 2f;
        [KSPField] public string experimentID = "xenoAnalysis";
        [KSPField] public string fossilExperimentID = "xenoFossilStudy";

        [KSPField(guiActive = true, guiName = "Xeno analysis")]
        public string status = "idle";

        [KSPField(isPersistant = true)] public bool running;
        [KSPField(isPersistant = true)] public string jobKey = "";
        [KSPField(isPersistant = true)] public string jobTitle = "";
        [KSPField(isPersistant = true)] public double jobProgress;      // seconds of 1x work done
        [KSPField(isPersistant = true)] public double lastUT = -1;

        struct Item { public string key, title; public float value; public CelestialBody body; }

        float uiTimer;

        public override string GetInfo()
        {
            return string.Format("Analyses xenobiology specimens (CO-Z units) and fossil samples carried on the vessel.\n<b>Time:</b> {0:F0} h per item, faster with more experienced scientists\n<b>Power:</b> {1:F1} EC/s while working\n<b>Each analysis:</b> new science and +1 evidence for the tree of life",
                hoursPerItem, ecPerSecond);
        }

        // ------------------------------------------------------------------ what can be analysed

        List<Item> Pending()
        {
            var list = new List<Item>();
            var scen = XenoScenario.Instance;
            if (scen == null || vessel == null) return list;
            var seen = new HashSet<string>();
            foreach (var coz in vessel.FindPartModulesImplementing<ModuleXenoContainment>())
                foreach (var s in coz.specimens)
                {
                    LifeformDef d;
                    if (!XenoDatabase.Lifeforms.TryGetValue(s.species, out d)) continue;
                    string key = "species:" + d.name;
                    if (scen.Analysed.Contains(key) || !seen.Add(key)) continue;
                    list.Add(new Item { key = key, title = d.displayName + " specimen", value = d.scienceValue * specimenMultiplier, body = d.celestialBody });
                }
            var fossils = XenoDatabase.Fossils.Values.OrderByDescending(f => f.name.Length).ToList();
            foreach (var box in vessel.FindPartModulesImplementing<IScienceDataContainer>())
                foreach (ScienceData data in box.GetData())
                {
                    if (data == null || data.subjectID == null || !data.subjectID.StartsWith(fossilExperimentID + "@")) continue;
                    FossilDef f = fossils.FirstOrDefault(x => data.subjectID.EndsWith("_" + x.name, StringComparison.Ordinal));
                    if (f == null) continue;
                    string key = "fossil:" + f.name;
                    if (scen.Analysed.Contains(key) || !seen.Add(key)) continue;
                    list.Add(new Item { key = key, title = f.displayName + " sample", value = f.scienceValue * fossilMultiplier, body = f.celestialBody });
                }
            return list;
        }

        /// <summary>Work rate from the scientists inside this part: 1 + 0.5 per level, summed over scientists.</summary>
        float Rate()
        {
            float r = 0f;
            foreach (ProtoCrewMember c in part.protoModuleCrew)
                if (c != null && c.experienceTrait != null && c.experienceTrait.TypeName == "Scientist") r += 1f + 0.5f * c.experienceLevel;
            return r;
        }

        double JobSeconds { get { return Math.Max(60.0, hoursPerItem * 3600.0); } }

        // ------------------------------------------------------------------ events

        [KSPEvent(guiActive = true, guiName = "Start Xeno Analysis")]
        public void StartAnalysis()
        {
            if (Rate() <= 0f) { ScreenMessages.PostScreenMessage("A scientist must be working in the lab.", 4f, ScreenMessageStyle.UPPER_CENTER); return; }
            if (string.IsNullOrEmpty(jobKey) && !NextJob())
            {
                ScreenMessages.PostScreenMessage("Nothing new to analyse: bring CO-Z specimens or fossil survey samples aboard.", 5f, ScreenMessageStyle.UPPER_CENTER);
                return;
            }
            running = true;
            lastUT = Planetarium.GetUniversalTime();
            ScreenMessages.PostScreenMessage("Analysing " + jobTitle + "…", 3f, ScreenMessageStyle.UPPER_CENTER);
            UpdateUI();
        }

        [KSPEvent(guiActive = true, guiName = "Stop Xeno Analysis", active = false)]
        public void StopAnalysis()
        {
            running = false;
            UpdateUI();
        }

        [KSPEvent(guiActive = true, guiName = "List Analysable Items")]
        public void ListPending()
        {
            var p = Pending();
            string s = p.Count == 0 ? "Nothing new to analyse on this vessel." : "Awaiting analysis:\n" + string.Join("\n", p.Select(x => x.title).ToArray());
            ScreenMessages.PostScreenMessage(s, 6f, ScreenMessageStyle.UPPER_CENTER);
        }

        bool NextJob()
        {
            var p = Pending();
            if (p.Count == 0) { jobKey = ""; jobTitle = ""; jobProgress = 0; return false; }
            jobKey = p[0].key; jobTitle = p[0].title; jobProgress = 0;
            return true;
        }

        // ------------------------------------------------------------------ work

        public override void OnStart(StartState state)
        {
            if (!HighLogic.LoadedSceneIsFlight) return;
            // catch up on work done while the vessel was unloaded (power is assumed)
            double now = Planetarium.GetUniversalTime();
            if (running && lastUT > 0 && now > lastUT && !string.IsNullOrEmpty(jobKey))
                jobProgress += (now - lastUT) * Rate();
            lastUT = now;
            UpdateUI();
        }

        public void FixedUpdate()
        {
            if (!HighLogic.LoadedSceneIsFlight || vessel == null) return;
            double now = Planetarium.GetUniversalTime();
            double dt = lastUT > 0 ? Math.Max(0.0, now - lastUT) : 0.0;
            lastUT = now;
            if (!running) return;
            float rate = Rate();
            if (rate <= 0f) return;
            if (string.IsNullOrEmpty(jobKey) && !NextJob()) { running = false; ScreenMessages.PostScreenMessage("Xeno analysis: all items analysed.", 4f, ScreenMessageStyle.UPPER_CENTER); return; }
            if (dt <= 0) return;
            double frac = 1.0;
            if (ecPerSecond > 0f)
            {   // at high warp the batteries may not cover a whole frame: work only as far as the power reaches
                double want = ecPerSecond * dt, got = part.RequestResource("ElectricCharge", want);
                frac = want > 0 ? Math.Min(1.0, got / want) : 1.0;
                if (frac < 0.05) { if (uiTimer <= 0f) status = "no power"; return; }
            }
            jobProgress += dt * rate * frac;
            if (jobProgress >= JobSeconds) Complete();
        }

        void Complete()
        {
            var item = Pending().FirstOrDefault(x => x.key == jobKey);
            string key = jobKey, title = jobTitle;
            jobKey = ""; jobTitle = ""; jobProgress = 0;
            if (item.key == null) { XenoLog.Info("Analysis of " + title + " abandoned: the sample is no longer aboard"); return; }

            var scen = XenoScenario.Instance;
            if (scen != null) scen.RecordAnalysis(key);
            ScreenMessages.PostScreenMessage("<color=#9FE0B0>Lab analysis complete: " + title + "</color>", 6f, ScreenMessageStyle.UPPER_CENTER);
            Deliver(item);
            if (!NextJob()) { running = false; ScreenMessages.PostScreenMessage("Xeno analysis: all items analysed.", 4f, ScreenMessageStyle.UPPER_CENTER); }
            UpdateUI();
        }

        void Deliver(Item item)
        {
            try
            {
                if (HighLogic.CurrentGame == null || HighLogic.CurrentGame.Mode == Game.Modes.SANDBOX) return;
                ScienceExperiment exp = ResearchAndDevelopment.GetExperiment(experimentID);
                if (exp == null) { XenoLog.Warn("Experiment " + experimentID + " not defined"); return; }
                CelestialBody body = item.body ?? vessel.mainBody;
                string src = item.key.Replace(':', '_');
                ScienceSubject subj = ResearchAndDevelopment.GetExperimentSubject(exp, ExperimentSituations.SrfLanded, src, item.title, body, "", "");
                subj.scienceCap = item.value * subj.subjectValue;
                string title = exp.experimentTitle + ": " + item.title + " (" + body.displayName.LocalizeRemoveGender() + ")";
                var data = new ScienceData(item.value * subj.dataScale, 1f, 0f, subj.id, title, false, part.flightID);
                ModuleScienceContainer box = XenoSettings.RequireRecoveryForScience ? vessel.FindPartModuleImplementing<ModuleScienceContainer>() : null;
                if (box != null && !box.HasData(data) && box.AddData(data))
                {
                    ScreenMessages.PostScreenMessage("Analysis results stored: " + item.title, 3f, ScreenMessageStyle.UPPER_LEFT);
                    return;
                }
                if (ResearchAndDevelopment.Instance != null)
                {
                    float sci = ResearchAndDevelopment.Instance.SubmitScienceData(data.dataAmount, subj, 1f, vessel.protoVessel, false);
                    ScreenMessages.PostScreenMessage(string.Format("Analysis results transmitted: +{0:F1} science", sci), 4f, ScreenMessageStyle.UPPER_LEFT);
                }
            }
            catch (Exception e) { XenoLog.Error("Analysis science failed: " + e); }
        }

        // ------------------------------------------------------------------ UI

        public void Update()
        {
            if (!HighLogic.LoadedSceneIsFlight) return;
            uiTimer -= Time.deltaTime;
            if (uiTimer > 0f) return;
            uiTimer = 1f;
            UpdateUI();
        }

        void UpdateUI()
        {
            Events["StartAnalysis"].active = !running;
            Events["StopAnalysis"].active = running;
            float rate = Rate();
            if (!running) status = string.IsNullOrEmpty(jobKey) ? "idle" : "paused: " + jobTitle;
            else if (rate <= 0f) status = "waiting for a scientist";
            else if (string.IsNullOrEmpty(jobKey)) status = "nothing to analyse";
            else
            {
                double left = (JobSeconds - jobProgress) / rate;
                status = string.Format("{0} {1:P0} ({2} left)", jobTitle, Mathf.Clamp01((float)(jobProgress / JobSeconds)), KSPUtil.PrintTimeCompact(Math.Max(0, left), false));
            }
        }
    }
}
