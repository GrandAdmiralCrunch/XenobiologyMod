using System;
using UnityEngine;

namespace Xenobiology
{
    /// <summary>
    /// Added to every EVA kerbal by ModuleManager. Lets kerbals observe nearby lifeforms
    /// and lets scientists study fossil outcrops. Results go into the kerbal's science
    /// container like any stock EVA science.
    /// </summary>
    public class ModuleXenoFieldKit : PartModule
    {
        [KSPField(guiActive = true, guiName = "Nearest life")]
        public string nearestLifeStatus = "—";

        [KSPField(guiActive = true, guiName = "Nearest fossil")]
        public string nearestFossilStatus = "—";

        FossilSite studying;
        float studyProgress, studyDuration;
        float uiTimer;
        ScreenMessage progressMsg;

        ProtoCrewMember Crew
        {
            get { return part.protoModuleCrew != null && part.protoModuleCrew.Count > 0 ? part.protoModuleCrew[0] : null; }
        }

        public override void OnStart(StartState state)
        {
            base.OnStart(state);
            if (!HighLogic.LoadedSceneIsFlight) return;
            progressMsg = new ScreenMessage("", 1f, ScreenMessageStyle.UPPER_CENTER);
        }

        // ------------------------------------------------------------------ observe

        [KSPEvent(guiActive = true, guiName = "Observe Lifeform", active = true)]
        public void ObserveLifeform()
        {
            var sp = XenoSpawner.Instance;
            if (sp == null || vessel == null) return;
            double dist;
            CreatureController c = sp.NearestCreature(vessel.GetWorldPos3D(), XenoSettings.DefaultObserveRange, out dist);
            // fixed life in a lair (corals, sponges): observed by swimming up to it
            LifeformDef sdef = null; double sd = double.MaxValue;
            LairInstance sl = LairManager.Instance != null ? LairManager.Instance.NearestSpecimen(vessel.GetWorldPos3D(), 60, out sdef, out sd) : null;
            if (sl != null && sd <= sdef.ObserveRange && (c == null || dist > c.def.ObserveRange || sd < dist)) { ObserveSpecimen(sl, sdef); return; }
            if (sl != null && c == null)
            {
                ScreenMessages.PostScreenMessage(string.Format("Swim closer to make out details ({0:F0} m, need {1:F0} m).", sd, sdef.ObserveRange), 3f, ScreenMessageStyle.UPPER_CENTER);
                return;
            }
            if (c == null)
            {
                ScreenMessages.PostScreenMessage("No lifeforms close enough to observe.", 3f, ScreenMessageStyle.UPPER_CENTER);
                return;
            }
            if (dist > c.def.ObserveRange)
            {
                ScreenMessages.PostScreenMessage(string.Format("Too far to make out details ({0:F0} m, need {1:F0} m).", dist, c.def.ObserveRange), 3f, ScreenMessageStyle.UPPER_CENTER);
                return;
            }
            string who = Crew != null ? Crew.name : vessel.vesselName;
            string biomeDisplay = ScienceUtil.GetBiomedisplayName(vessel.mainBody, c.biome);
            bool isNew = XenoScenario.Instance != null && XenoScenario.Instance.RecordObservation(c.def, who, biomeDisplay);
            c.observed = true;
            if (!isNew)
                ScreenMessages.PostScreenMessage("Observed: " + c.def.displayName, 3f, ScreenMessageStyle.UPPER_CENTER);
            XenoScience.Collect(this, "xenoObservation", c.def.name, c.def.displayName, c.def.scienceValue, c.biome,
                "Field notes on " + c.def.displayName + ". " + c.def.description);
        }

        void ObserveSpecimen(LairInstance l, LifeformDef d)
        {
            var scen = XenoScenario.Instance;
            string who = Crew != null ? Crew.name : vessel.vesselName;
            string biome = Geo.Biome(vessel.mainBody, vessel.latitude, vessel.longitude);
            bool wasAll = l.AllCatalogued();
            bool isNew = scen != null && scen.RecordObservation(d, who, ScienceUtil.GetBiomedisplayName(vessel.mainBody, biome));
            int total, known = l.CataloguedCount(out total);
            if (!isNew) ScreenMessages.PostScreenMessage("Observed: " + d.displayName, 3f, ScreenMessageStyle.UPPER_CENTER);
            else ScreenMessages.PostScreenMessage(string.Format("<color=#9FE0FF>{0} catalogued ({1} of {2} at the {3})</color>", d.displayName, known, total, l.def.displayName), 5f, ScreenMessageStyle.UPPER_CENTER);
            XenoScience.Collect(this, "xenoObservation", d.name, d.displayName, d.scienceValue, biome, "Field notes on " + d.displayName + ". " + d.description);
            if (!wasAll && l.AllCatalogued() && l.def.catalogueScience > 0)
            {
                ScreenMessages.PostScreenMessage("<color=#FFD27F>Every species at the " + l.def.displayName + " has been catalogued!</color>", 8f, ScreenMessageStyle.UPPER_CENTER);
                XenoScience.Collect(this, "xenoLairSurvey", l.def.name + "_catalogue", l.def.displayName + " Catalogue", l.def.catalogueScience, biome,
                    "A complete species list for the " + l.def.displayName + ", with sketches of every coral, sponge and anemone and notes on where each one grows.");
            }
        }

        static readonly System.Collections.Generic.HashSet<string> hinted = new System.Collections.Generic.HashSet<string>();

        // ------------------------------------------------------------------ lairs

        [KSPEvent(guiActive = true, guiName = "Survey Lair", active = false)]
        public void SurveyLair()
        {
            var lm = LairManager.Instance;
            LairInstance l = lm != null ? lm.InsideOf(vessel) : null;
            if (l == null) { ScreenMessages.PostScreenMessage("You need to be inside a lair to survey it.", 3f, ScreenMessageStyle.UPPER_CENTER); return; }
            string who = Crew != null ? Crew.name : vessel.vesselName;
            var scen = XenoScenario.Instance;
            LairRecord rec = LairManager.Site(l.def);
            if (rec != null && string.IsNullOrEmpty(rec.surveyedBy))
            {
                rec.surveyedBy = who;
                ScreenMessages.PostScreenMessage("<color=#C8B08A>" + who + " sketches the inside of the " + l.def.displayName + ".</color>", 5f, ScreenMessageStyle.UPPER_CENTER);
                if (KSP.UI.Screens.MessageSystem.Instance != null)
                    KSP.UI.Screens.MessageSystem.Instance.AddMessage(new KSP.UI.Screens.MessageSystem.Message("Lair surveyed: " + l.def.displayName,
                        who + " made it inside and back out (so far).\n\n" + (string.IsNullOrEmpty(l.def.surveyText) ? l.def.description : l.def.surveyText),
                        KSP.UI.Screens.MessageSystemButton.MessageButtonColor.ORANGE, KSP.UI.Screens.MessageSystemButton.ButtonIcons.ACHIEVE));
            }
            XenoScience.Collect(this, "xenoLairSurvey", l.def.name, l.def.displayName, l.def.scienceValue, Geo.Biome(vessel.mainBody, vessel.latitude, vessel.longitude),
                "Measurements and sketches from inside the " + l.def.displayName + ". " + l.def.description);
        }

        // ------------------------------------------------------------------ specimens

        const float CaptureRange = 40f, ContainerRange = 150f;

        static ModuleXenoContainment NearestContainer(Vessel me, out double dist)
        {
            dist = double.MaxValue;
            ModuleXenoContainment best = null;
            Vector3d p = me.GetWorldPos3D();
            foreach (Vessel v in FlightGlobals.VesselsLoaded)
            {
                if (v == null || v == me || v.isEVA) continue;
                foreach (Part pt in v.parts)
                {
                    var m = pt.FindModuleImplementing<ModuleXenoContainment>();
                    if (m == null) continue;
                    double d = (pt.transform.position - (Vector3)p).magnitude;
                    if (d < dist) { dist = d; best = m; }
                }
            }
            return best;
        }

        CreatureController NearestCatchable(out double dist)
        {
            dist = double.MaxValue;
            CreatureController best = null;
            var sp = XenoSpawner.Instance;
            if (sp == null) return null;
            Vector3d me = vessel.GetWorldPos3D();
            foreach (var c in sp.Creatures)
            {
                if (c == null || c.state == CreatureState.Underground || c.Ridden || c.lair != null) continue;
                double d = (c.WorldPos - me).magnitude;
                if (d <= CaptureRange && d < dist) { dist = d; best = c; }
            }
            return best;
        }

        [KSPEvent(guiActive = true, guiName = "Capture Specimen", active = false)]
        public void CaptureSpecimen()
        {
            var sp = XenoSpawner.Instance;
            if (sp == null) return;
            double dc, dk;
            CreatureController c = NearestCatchable(out dk);
            if (c == null) { ScreenMessages.PostScreenMessage("Nothing close enough to catch (within " + CaptureRange + " m).", 3f, ScreenMessageStyle.UPPER_CENTER); return; }
            ModuleXenoContainment box = NearestContainer(vessel, out dc);
            if (box == null || dc > ContainerRange)
            {
                ScreenMessages.PostScreenMessage("No CO-Z Containment Unit within " + ContainerRange + " m to put it in.", 4f, ScreenMessageStyle.UPPER_CENTER);
                return;
            }
            string why = box.WhyNot(c.def);
            if (why != null) { ScreenMessages.PostScreenMessage(why, 5f, ScreenMessageStyle.UPPER_CENTER); return; }
            if (c.state == CreatureState.Flee && UnityEngine.Random.value < 0.5f)
            {
                c.Startle(UnityEngine.Random.Range(0f, 360f));
                ScreenMessages.PostScreenMessage("The " + c.def.displayName + " slips away. Try again when it calms down.", 3f, ScreenMessageStyle.UPPER_CENTER);
                return;
            }
            string who = Crew != null ? Crew.name : vessel.vesselName;
            string biomeDisplay = ScienceUtil.GetBiomedisplayName(c.body, c.biome);
            if (XenoScenario.Instance != null) XenoScenario.Instance.RecordObservation(c.def, who, biomeDisplay);
            box.Store(c, who);
            sp.Creatures.Remove(c);
            UnityEngine.Object.Destroy(c.gameObject);
            ScreenMessages.PostScreenMessage("<color=#7CFC9A>" + who + " coaxes the " + c.def.displayName + " into the " + box.part.partInfo.title + ".</color>", 4f, ScreenMessageStyle.UPPER_CENTER);
        }

        // ------------------------------------------------------------------ riding

        [KSPEvent(guiActive = true, guiName = "Mount Creature", active = false)]
        public void MountCreature()
        {
            var mc = MountController.Instance;
            if (mc == null) return;
            if (MountController.IsRiding(vessel)) mc.Dismount();
            else mc.TryMount(vessel);
        }

        // ------------------------------------------------------------------ fossils

        [KSPEvent(guiActive = true, guiName = "Study Fossil", active = true)]
        public void StudyFossil()
        {
            var sp = XenoSpawner.Instance;
            if (sp == null) return;
            if (studying != null) { CancelStudy("Study cancelled."); return; }

            double dist;
            FossilSite s = sp.NearestSite(vessel.GetWorldPos3D(), XenoSettings.FossilStudyRange * Mathf.Max(1f, 1f), out dist);
            if (s == null)
            {
                FossilSite far = sp.NearestSite(vessel.GetWorldPos3D(), 500f, out dist);
                ScreenMessages.PostScreenMessage(far == null ? "No fossil-bearing rock nearby." : string.Format("Move closer to the outcrop ({0:F0} m).", dist), 3f, ScreenMessageStyle.UPPER_CENTER);
                return;
            }
            if (s.studied)
            {
                ScreenMessages.PostScreenMessage("This outcrop has already been studied.", 3f, ScreenMessageStyle.UPPER_CENTER);
                return;
            }
            ProtoCrewMember k = Crew;
            if (!string.IsNullOrEmpty(s.def.requiredTrait) && (k == null || !string.Equals(k.trait, s.def.requiredTrait, StringComparison.OrdinalIgnoreCase)))
            {
                ScreenMessages.PostScreenMessage("Only a " + s.def.requiredTrait + " can interpret these fossils.", 4f, ScreenMessageStyle.UPPER_CENTER);
                return;
            }
            int lvl = k != null ? k.experienceLevel : 0;
            if (lvl < s.def.minLevel)
            {
                ScreenMessages.PostScreenMessage(string.Format("Needs a level {0} {1} — the specimen is too fragile.", s.def.minLevel, s.def.requiredTrait), 4f, ScreenMessageStyle.UPPER_CENTER);
                return;
            }
            studying = s;
            studyProgress = 0f;
            studyDuration = s.def.studyTime / (1f + 0.35f * lvl);
            ScreenMessages.PostScreenMessage("Studying the outcrop… stay close.", 3f, ScreenMessageStyle.UPPER_CENTER);
        }

        void CancelStudy(string why)
        {
            studying = null;
            ScreenMessages.RemoveMessage(progressMsg);
            if (!string.IsNullOrEmpty(why)) ScreenMessages.PostScreenMessage(why, 3f, ScreenMessageStyle.UPPER_CENTER);
        }

        void CompleteStudy()
        {
            FossilSite s = studying;
            studying = null;
            ScreenMessages.RemoveMessage(progressMsg);
            string who = Crew != null ? Crew.name : vessel.vesselName;
            s.MarkStudied();
            bool isNew = XenoScenario.Instance != null && XenoScenario.Instance.RecordFossil(s.def, s.siteId, who);
            if (!isNew) ScreenMessages.PostScreenMessage("Another " + s.def.displayName + " specimen recorded.", 3f, ScreenMessageStyle.UPPER_CENTER);
            XenoScience.Collect(this, "xenoFossilStudy", s.def.name, s.def.displayName, s.def.scienceValue, Geo.Biome(vessel.mainBody, s.lat, s.lon),
                "Stratigraphic notes and sketches of " + s.def.displayName + ". " + s.def.description);
        }

        // ------------------------------------------------------------------ per-frame

        public void Update()
        {
            if (!HighLogic.LoadedSceneIsFlight || vessel == null) return;
            var sp = XenoSpawner.Instance;
            if (sp == null) return;

            if (studying != null)
            {
                if (studying == null || studying.DistanceTo(vessel.GetWorldPos3D()) > XenoSettings.FossilStudyRange * 1.5f)
                    CancelStudy("Moved away from the outcrop; study interrupted.");
                else
                {
                    studyProgress += TimeWarp.deltaTime;
                    progressMsg.message = string.Format("Studying {0}: {1:P0}", studying.def.displayName, Mathf.Clamp01(studyProgress / studyDuration));
                    ScreenMessages.PostScreenMessage(progressMsg);
                    if (studyProgress >= studyDuration) CompleteStudy();
                }
            }

            if (vessel == FlightGlobals.ActiveVessel && XenoSettings.ObserveKey != KeyCode.None && Input.GetKeyDown(XenoSettings.ObserveKey)
                && !InputLockManager.IsLocked(ControlTypes.ALL_SHIP_CONTROLS) && GUIUtility.keyboardControl == 0)
                ObserveLifeform();

            uiTimer -= Time.deltaTime;
            if (uiTimer > 0) return;
            uiTimer = 0.5f;

            Vector3d me = vessel.GetWorldPos3D();
            double d;
            CreatureController c = sp.NearestCreature(me, 2000f, out d);
            LifeformDef sdef = null; double sd = double.MaxValue;
            LairInstance sl = LairManager.Instance != null ? LairManager.Instance.NearestSpecimen(me, 60, out sdef, out sd) : null;
            if (sl != null && (c == null || sd < d || (sd <= sdef.ObserveRange && d > c.def.ObserveRange)))
            {
                bool known = XenoScenario.Instance != null && XenoScenario.Instance.IsDiscovered(sdef);
                string nm = known ? sdef.displayName : "Unidentified " + (string.IsNullOrEmpty(sdef.guideCategory) ? "lifeform" : sdef.guideCategory);
                int total, cat = sl.CataloguedCount(out total);
                nearestLifeStatus = string.Format("{0}, {1:F0} m{2} [{3}/{4}]", nm, sd, sd <= sdef.ObserveRange ? " (in range)" : "", cat, total);
                Events["ObserveLifeform"].guiName = sd <= sdef.ObserveRange ? "Observe " + nm : "Observe Lifeform";
                if (!known && sd <= sdef.ObserveRange + 4 && vessel == FlightGlobals.ActiveVessel && hinted.Add(sdef.name))
                    ScreenMessages.PostScreenMessage("Something unfamiliar grows here - Observe it (" + XenoSettings.ObserveKey + ")", 4f, ScreenMessageStyle.UPPER_CENTER);
            }
            else if (c != null)
            {
                bool known = XenoScenario.Instance != null && XenoScenario.Instance.IsDiscovered(c.def);
                string nm = known ? c.def.displayName : "Unidentified lifeform";
                nearestLifeStatus = string.Format("{0}, {1:F0} m{2}", nm, d, d <= c.def.ObserveRange ? " (in range)" : "");
                Events["ObserveLifeform"].guiName = d <= c.def.ObserveRange ? "Observe " + nm : "Observe Lifeform";
            }
            else { nearestLifeStatus = "none detected"; Events["ObserveLifeform"].guiName = "Observe Lifeform"; }

            if (MountController.IsRiding(vessel))
            {
                Events["MountCreature"].active = true;
                Events["MountCreature"].guiName = "Dismount (" + XenoSettings.MountKey + ")";
            }
            else
            {
                string why;
                CreatureController mountable = MountController.FindMountable(vessel, out why);
                bool near = false;
                foreach (var cc in sp.Creatures) if (cc != null && cc.def.mount != null && (cc.WorldPos - me).magnitude < cc.def.mount.mountRange * 3) { near = true; break; }
                Events["MountCreature"].active = near;
                Events["MountCreature"].guiName = mountable != null ? "Mount " + mountable.def.displayName + " (" + XenoSettings.MountKey + ")" : "Mount (needs a sleeping animal)";
            }

            FossilSite fs = sp.NearestSite(me, 2000f, out d);
            if (fs != null)
            {
                double brg = Geo.Bearing(vessel.mainBody, vessel.latitude, vessel.longitude, fs.lat, fs.lon);
                nearestFossilStatus = string.Format("{0:F0} m {1}{2}", d, Geo.CompassName(brg), fs.studied ? " (studied)" : "");
                Events["StudyFossil"].guiActive = true;
                Events["StudyFossil"].guiName = studying != null ? "Cancel Fossil Study" : "Study Fossil";
            }
            else { nearestFossilStatus = "none nearby"; Events["StudyFossil"].guiActive = studying != null; }

            double dcap; CreatureController catchable = NearestCatchable(out dcap);
            Events["CaptureSpecimen"].active = catchable != null;
            if (catchable != null) Events["CaptureSpecimen"].guiName = "Capture " + (XenoScenario.Instance != null && XenoScenario.Instance.IsDiscovered(catchable.def) ? catchable.def.displayName : "Lifeform");
            Events["SurveyLair"].active = LairManager.Instance != null && LairManager.Instance.InsideOf(vessel) != null;
        }
    }

    public static class XenoScience
    {
        /// <summary>
        /// Produces one ScienceData per (experiment, species/fossil, biome) and stores it in the
        /// kerbal's container, or submits it directly if the settings say so.
        /// </summary>
        public static void Collect(PartModule pm, string experimentId, string sourceId, string sourceTitle, float value, string biome, string resultText, string storedVerb = "Field notes stored")
        {
            try
            {
                if (HighLogic.CurrentGame == null || HighLogic.CurrentGame.Mode == Game.Modes.SANDBOX) return;
                ScienceExperiment exp = ResearchAndDevelopment.GetExperiment(experimentId);
                if (exp == null) { XenoLog.Warn("Experiment " + experimentId + " not defined"); return; }
                Vessel v = pm.vessel;
                CelestialBody body = v.mainBody;
                ExperimentSituations sit = ScienceUtil.GetExperimentSituation(v);
                string b = string.IsNullOrEmpty(biome) ? "" : biome;
                ScienceSubject subj = ResearchAndDevelopment.GetExperimentSubject(exp, sit, sourceId, sourceTitle, body, b, ScienceUtil.GetBiomedisplayName(body, b));
                subj.scienceCap = value * subj.subjectValue;
                float amount = value * subj.dataScale;
                string title = exp.experimentTitle + ": " + sourceTitle + " (" + body.displayName.LocalizeRemoveGender() + ")";
                var data = new ScienceData(amount, 1f, 0f, subj.id, title, false, pm.part.flightID);

                if (!XenoSettings.RequireRecoveryForScience && ResearchAndDevelopment.Instance != null)
                {
                    float sci = ResearchAndDevelopment.Instance.SubmitScienceData(amount, subj, 1f, v.protoVessel, false);
                    ScreenMessages.PostScreenMessage(string.Format("+{0:F1} science", sci), 3f, ScreenMessageStyle.UPPER_LEFT);
                    return;
                }
                ModuleScienceContainer box = pm.part.FindModuleImplementing<ModuleScienceContainer>();
                if (box == null && v != null) box = v.FindPartModuleImplementing<ModuleScienceContainer>();
                if (box == null) { XenoLog.Warn("No science container on " + pm.part.partInfo.name); return; }
                if (box.HasData(data))
                {
                    ScreenMessages.PostScreenMessage("Already carrying notes on " + sourceTitle + " from here.", 3f, ScreenMessageStyle.UPPER_LEFT);
                    return;
                }
                if (subj.science >= subj.scienceCap - 0.01f)
                {
                    ScreenMessages.PostScreenMessage("Nothing new to learn about " + sourceTitle + " here (science cap reached).", 3f, ScreenMessageStyle.UPPER_LEFT);
                    return;
                }
                if (box.AddData(data))
                    ScreenMessages.PostScreenMessage(storedVerb + ": " + sourceTitle, 3f, ScreenMessageStyle.UPPER_LEFT);
            }
            catch (Exception e) { XenoLog.Error("Science collection failed: " + e); }
        }
    }
}
