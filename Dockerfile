FROM fnndsc/python-poetry
COPY pyproject.toml ./
COPY src ./src

RUN poetry install
# RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python - && \
#     $HOME/.poetry/bin/poetry install

# USER root
# ENV PATH=/root/.poetry/bin:$PATH

ENTRYPOINT ["poetry", "run"]