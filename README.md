
diff --git a/README.md b/README.md
index 7f9b1aa..2a4bd11 100644
--- a/README.md
+++ b/README.md
@@ -12,6 +12,20 @@
 fly secrets set OCTOPUS_API_KEY=sk_live_xxx
 fly secrets set ELEC_MPAN=xxxxxxxxxxxx
 fly secrets set ELEC_SERIAL=xxxxxxxx
+fly secrets set ELEC_STANDING_CHARGE=53.2            # p/day (electricity)
 fly secrets set GAS_MPRN=xxxxxxxxxxxx
 fly secrets set GAS_SERIAL=xxxxxxxx
 fly secrets set GAS_UNIT_RATE=6.89                   # p/kWh
 fly secrets set GAS_STANDING_CHARGE=27.47            # p/day
+
+# Agile tariff config (optional; defaults provided)
+fly secrets set AGILE_PRODUCT_CODE=AGILE-24-10-01
+fly secrets set AGILE_TARIFF_CODE=E-1R-AGILE-24-10-01-A
+
+# Notes
+- Electricity cost now includes standing charge when ELEC_STANDING_CHARGE is set.
+- Timestamp alignment is DST-safe: consumption `interval_start` and prices `valid_from` are normalized to UTC and matched by slot.
+- Today’s Agile prices are cached server-side per day to reduce API calls; cache resets at midnight local time.
+
 fly deploy
