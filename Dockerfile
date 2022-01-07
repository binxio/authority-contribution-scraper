FROM python:3.9-slim

ENV APP_HOME /app
WORKDIR $APP_HOME

COPY Pipfile ./
RUN pip install $(sed -n -e '/^\[packages\]/,/^\[/p' Pipfile |sed -e '/^\[/d' -e 's/ = .*//' -e '/^$/d')

COPY src ./

EXPOSE 8080
ENV PORT 8080
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 authority.app:app
