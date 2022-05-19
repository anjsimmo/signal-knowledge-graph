# Signal Knowledge Graph

## Motivation and purpose

This project provides an RDF/OWL ontology (`signal.ttl`) for representing different kinds of signals (sound/audio, vision, etc.) in a way that facilitates reasoning and sensor integration. For example, it can be used to infer the probability of an attacker given observations from different types of sensors.

## Dependencies

For editing `signal.ttl`:
* An RDF/OWL editor, such as Protégé (open source) or TopBraid Composer (recommended)

For inference:
* Python3
* [rdflib](https://github.com/RDFLib/rdflib)

For visualisation/inference with R:
* R
* [bnlearn](https://www.bnlearn.com/)

## Running it

1. (Optional) Modify/extend `signal.ttl` to include sensor observation instances and new signal types.
2. `python3 infer.py` to infer the probability of an attacker. This will output results on the command line, as well as generating a Bayesian network in `infer.bif`.
3. `RScript bayesvis.R` to perform inference with bnlearn (results should be similar to those produced by `infer.py`) and to visualise the graph (will generate `infer_graph.pdf`).

