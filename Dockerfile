FROM python:3.11

ENV APP_HOME /app
WORKDIR $APP_HOME

COPY Pipfile ./
RUN pip install $(sed -n -e '/^\[packages\]/,/^\[/p' Pipfile |sed -e '/^\[/d' -e 's/ = .*//' -e '/^$/d' -e 's/"//g')

COPY src ./

EXPOSE 8080
ENV PORT 8080
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 authority.app:app
