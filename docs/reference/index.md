# Code structure and reference

!!! warning "This section is in development"
    Some submodules are missing. We also do not strive for completeness, but provide this as an easy entry point
    for people who want to start reading the code.
    Also note that SWE-agent is still developed very actively, so the python implementation details
    are still changing. See [the changelog](../installation/changelog.md) for more information.

The core:

* The `sweagent/agent/` []() submodule implements the agent.
    * [Read about the `Agent` class](agent.md)
    * [Explore the code](https://github.com/princeton-nlp/SWE-agent/tree/main/sweagent/agent/)
* The `sweagent/environment/` submodule handles the communication with the docker container where we execute code.
    * [Read about the `SWEEnv` class](agent.md)
    * [Explore the code](https://github.com/princeton-nlp/SWE-agent/tree/main/sweagent/environment/)

More subolders

* See the [`scripts/`](https://github.com/princeton-nlp/SWE-agent/tree/main/scripts/) folder for other useful scripts and details.
* See the [`config/`](https://github.com/princeton-nlp/SWE-agent/tree/main/config/) folder for details about how you can define your own configuration!
* See the [`trajectories/`](https://github.com/princeton-nlp/SWE-agent/tree/main/trajectories) folder for details about the output of `run.py`.
* See the [`evaluation/`](https://github.com/princeton-nlp/SWE-agent/tree/main/evaluation/) folder for details about how evaluation works.
