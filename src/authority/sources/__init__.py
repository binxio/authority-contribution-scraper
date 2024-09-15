"""
Module containing all authority contribution sources.
Imports all sources to automatically register them to the factory.
"""
from authority.sources.youtube import YoutubeChannel
from authority.sources.blog import BlogSource
from authority.sources.xke import XkeSource
from authority.sources.article import AuthoritySource
from authority.sources.github_pull_requests import GithubPullRequests
