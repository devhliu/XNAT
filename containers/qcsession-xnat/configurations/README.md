## Additional Command Configurations

Using the same docker image we can create a number of unique Command Configurations which provide
different entry points for orchestration.

1. Bids conversion only (proc=bidsconvert) - which can then be linked to other workflows
2. Phantom (proc=bidsconvert, phantomqc) which performs bidsconversion and then the phantom pipeline
