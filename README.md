# SBOM Kickstart demo

The path the [SBOM Kickstart](https://rebaze.de/sbom-kickstart/) sets up, on a demo product:

1. **The build writes the SBOM.** `partner-portal/` is a small Maven backend; the CycloneDX plugin writes `target/bom.json` from the resolved dependencies.
2. **The SBOM is checked** against BSI TR-03183-2 v2.1 with sbomqs. The missing required fields are listed in the run's summary.
3. **The policy gate** (`scripts/gate.py`) uploads the SBOM to Dependency-Track, waits for the evaluation and stops the build on a violation with state FAIL. Each violation names the rule and why the rule exists (`policies/sources.json`).

4. **The register of CRA obligations** (`scripts/register.py`) writes one Excel workbook per product and release from `register/*.json`: state, evidence, next step and effort per obligation.

`main` builds release 2016.4 and passes. The branch `hotfix/2016.4.1` pulls in log4j-core 2.14.1 (Log4Shell) and is stopped.

Everything here is illustrative: the product, its owner and the rules' thresholds. It contains no customer data.

## Run it

```sh
cd partner-portal && mvn -B -q package
DT_URL=https://dependencytrack.example DT_API_KEY=... \
  python3 ../scripts/gate.py target/bom.json "Partner Portal backend" 2016.4
```
