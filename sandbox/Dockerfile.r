# Supply a reviewed r-base Linux image by immutable digest at build time.
# Add/review any additional R packages required by your benchmark before building.
ARG BASE_IMAGE
FROM ${BASE_IMAGE}
USER 65534:65534
