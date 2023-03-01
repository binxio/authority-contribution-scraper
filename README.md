# Authority Contribution Scraper

The Authority Contribution Scraper is a tool we use to gather contributions that contribute to our
authority mission. At the moment it supports XKEs (Xebia Knowledge Exchange) sessions for Xebia Cloud and
blogposts and Github Pull Requests for Binx. Our goal is to make this tool work for all units
within Xebia.

## Deployment
The Authority Contribution Scraper is automatically deployed to Cloud Run by Cloud Build when the version
in the .release file is bumped and a tag is created. The Cloud Run url is triggered by Cloud Scheduler once
every hour, after which the Authority Contribution Scraper will write new entries to BigQuery.



## Development
Set the CLOUDSDK_PYTHON environment to a non-venv Python install corresponding to the requirements listed
[here](https://cloud.google.com/sdk/docs/install).

## Release and deploy
To release a new version of the scraper, type:

```shell
$ pip install git-release-tag
$ git-release-tag bump --level [patch|minor|major]
$ git push && git push --tags
```

It will be automatically deployed.
