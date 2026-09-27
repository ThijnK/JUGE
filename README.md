# JUGE for MAZE

This fork of [JUGE](https://github.com/JUnitContest/JUGE) benchmarks
[MAZE](https://github.com/ThijnK/maze) and other Java test generators using coverage,
mutation analysis and repeated experiments.

- **[AST2027 experiments](experiments/ast2027/README.md):** reproduce the current
  study, inspect progress, resume runs and regenerate statistics from saved data.
- **[MAZE integration](docs/MAZE.md):** run packaged MAZE with built-in or external
  search strategies and your own benchmark configurations.
- **[Seeded tool provisioning](tools/seeded/README.md):** pinned EvoSuite, Kex and
  T3 deployments used by the current experiments.
- **[Historical results](https://github.com/ThijnK/JUGE/releases):** 2025 thesis/paper
  and 2026 experiment archives, including study-specific analysis scripts.

MAZE is downloaded as a separate packaged release. AST2027 requires Docker and
Python on the host; a MAZE source checkout is unnecessary. Experiment outputs are
saved outside version-controlled sources and can be distributed as release assets.
Personal scheduling and notification instructions belong in ignored `local/`.

## Original JUGE README

Here you will find the source code to the JUGE and instructions on how to test your tool with the infrastructure.

For information about the past editions of the JUnit Competition, see [https://junitcontest.github.io](https://junitcontest.github.io).

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.4904393.svg)](https://doi.org/10.5281/zenodo.4904393)

## Documentation

See [docs/README.md](docs/USERGUIDE.md) for the user guide and [docs/DEVELOPERS.md](docs/CONTRIBUTORGUIDE.md) for the contributor guide.

More information about the infrastructure and how it can be used to set up an empirical evaluation for unit test generators can be found in [Devroey, X., Gambi, A., Galeotti, J. P., Just, R., Kifetew, F., Panichella, A., Panichella, S. (2021). JUGE: An Infrastructure for Benchmarking Java Unit Test Generators. Softw. Test. Verification Reliab. 33(3) (2023)](<[https://arxiv.org/abs/2106.07520](https://onlinelibrary.wiley.com/doi/full/10.1002/stvr.1838)>)

## Referencing JUGE

If you use JUGE in your evaluation, please include the following reference to your paper:

```bibtex
@article{Devroey2022,
  author = {Devroey, Xavier and Gambi, Alessio and Galeotti, Juan Pablo and Just, René and Kifetew, Fitsum and Panichella, Annibale and Panichella, Sebastiano},
  title = {JUGE: An infrastructure for benchmarking Java unit test generators},
  journal = {Software Testing, Verification and Reliability},
  pages = {e1838},
  doi = {https://doi.org/10.1002/stvr.1838},
}
```

# License

```
The JUnit Infrustructure support the generation an comparison of JUnit testing tools for Java projects.
Copyright (C) - Contributors and chairs of the JUnit Infrustructure.

The JUnit Infrustructure is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
```
