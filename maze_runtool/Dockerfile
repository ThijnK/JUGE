# Development-only checks of the adapter and generation/metrics gates.
FROM eclipse-temurin:8-jdk-noble@sha256:c220651a87a3da8287e7cb9c85252747f27b8360149e0f70f6277aa597ae5bac AS java8
FROM maven:3.9.16-eclipse-temurin-21-noble@sha256:a972570be789ee5c9fa23446a8914ac7327560b5c022f662cfa9452aef829f18
RUN sed -i 's/^Components:.*/Components: main/' /etc/apt/sources.list.d/ubuntu.sources \
    && apt-get update && apt-get install -y --no-install-recommends python3 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=java8 /opt/java/openjdk /opt/java8
WORKDIR /juge
