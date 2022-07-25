FROM fnndsc/python-poetry
COPY pyproject.toml ./
COPY src ./src

RUN poetry install

ENTRYPOINT ["poetry", "run"]