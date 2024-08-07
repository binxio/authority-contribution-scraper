"""
Module containing all authority contribution sources.
Imports all sources to automatically register them to the factory.
"""
from authority.sources.blog import BlogSource
from authority.sources.github_pull_requests import GithubPullRequests
from authority.sources.xke import XkeSource
from authority.sources.article import AuthoritySource
