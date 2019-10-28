### BASE DOCKER IMAGE

This branch is only meant to build the base docker image to speed up builds.

A cron job in travis will use this branch to build that daily.

The base image is `gcr.io/neuromancer-seung-import/pychunkedgraph:graph-tool_dracopy`