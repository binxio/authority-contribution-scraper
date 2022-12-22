SHELL := /bin/bash
deployit:
	@echo -n working. && while [[ $$(gcloud builds list  --format json | jq -r  --arg revid $$(git rev-parse head) 'map(select(.source.repoSource.commitSha == $$revid)|.status)[0]') =~ (WORKING|null) ]]; do \
		echo -n "." ; \
		sleep 2; \
	done ; \
	echo ; echo done ; \
	cru update $$( gcloud builds list  --format json | jq -r  --arg revid $$(git rev-parse head) 'map(select(.status == "SUCCESS" and .source.repoSource.commitSha == $$revid)|(.images | map("--image-reference " + .)) |.[]) | .[]' ) terraform && \
	cd terraform && \
	GOOGLE_OAUTH_ACCESS_TOKEN=$$(gcloud auth print-access-token) terraform apply --auto-approve
	





