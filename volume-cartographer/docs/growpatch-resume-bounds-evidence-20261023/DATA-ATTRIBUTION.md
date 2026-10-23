# Data and code attribution

The real surface prediction and published mesh come from the Vesuvius Challenge Open Data Catalog, PHerc0139, volume `20250728140407`. The archived publisher-catalog attribution identifies the data terms as CC BY-NC 4.0. Preserve that attribution and the publisher's applicable terms. Exact public S3 object URLs, original byte lengths and SHA-256 hashes are listed in `fixture-sources.json`; no private archive is required by the download script.

Prediction source: `https://vesuvius-challenge-open-data.s3.amazonaws.com/PHerc0139/representations/predictions/surfaces/20250728140407-surface-20260413222639-surface-m7-L0-th0.2.zarr/`.

Mesh source: `https://vesuvius-challenge-open-data.s3.amazonaws.com/PHerc0139/segments/20260311000000-w023_202603112281/mesh/20260311000000-on-20250728140407-9.362um.tifxyz/`.

The downloaded prediction chunks remain byte-identical to those public objects. Their chunk keys are relocated into a bounded Zarr ROI with generated local shape/OME/provenance metadata; the integer source offset is ZYX `(4224,3456,3456)`, equivalently XYZ `(3456,3456,4224)`. This is real surface-prediction data, not raw CT.

The public mesh source set contains `meta.json` and the three original XYZ TIFFs. The 5×5 fixture geometry is a crop of those actual Float32 points, with an exactly reversible integer translation. No artificial geometry holes are inserted. `generations.tif` is newly initialized to one at every fixture vertex for this bounded resume test. It is not an original published generation channel or a preserved real tracing history. Fixture UUID, translated bounding box and provenance metadata are generated test metadata. The source-file byte hashes, reconstructed fixture-file byte hashes, and separate decoded XYZ hashes have distinct meanings and are checked separately.

All three crops share the same prediction carrier. They are not independent scrolls or independent physical CT evaluations. The endpoint is compliance with a requested grid extent; no physical sheet, ink, readability or generalization improvement follows from fixture preparation.

ScrollPrize/villa remains attributed to its contributors. The repository-root MIT text is preserved separately in `LICENSE-ROOT-MIT.txt`; the existing `volume-cartographer` GPLv3 text is preserved in `LICENSE-VOLUME-CARTOGRAPHER-GPLv3.txt`. The combined volume-cartographer source remains subject to its existing license; this patch does not relicense it. A separate MIT grant for newly authored additions/helpers, if supplied, applies to those additions and does not replace the existing subproject license. Public-data CC BY-NC terms concern the data, separately from code licensing.

PR #2133 by alexeygoncharov already describes the rectangular-path limitation, and PR #2134 by vincentl065 concerns related border behavior. This current-main candidate does not incorporate their scheduling/border implementations. No first-discovery credit is claimed for the known limitation.

The proposed guard, validation/reconstruction tooling and reporting were prepared with AI assistance. Automated source/run checks do not establish personal human review. Public submission and personal verification status must be taken from the final completed release, not inferred from this attribution file.
