UCS_BASE := 5.0-1
UCS_BASE_ERRATA := 378
UCS_TARGET := 5.0-2
ERRATA_LEVEL := 471

IMAGE_NAME := unv-$(UCS_TARGET)
TARGET_TAG := $(IMAGE_NAME):$(ERRATA_LEVEL)

.PHONY: image

image: Dockerfile
	docker build \
		--build-arg UCS_BASE=$(UCS_BASE) \
		--build-arg UCS_BASE_ERRATA=$(UCS_BASE_ERRATA) \
		--build-arg UCS_TARGET=$(UCS_TARGET) \
		--build-arg ERRATA_LEVEL=$(ERRATA_LEVEL) \
		--tag "$(TARGET_TAG)" .
	docker tag "$(TARGET_TAG)" "$(IMAGE_NAME):latest"
