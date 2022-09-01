UCS_BASE := 4.4-4
UCS_TARGET := 4.4-5
ERRATA_LEVEL := 817

IMAGE_NAME := unv-$(UCS_TARGET)
TARGET_TAG := $(IMAGE_NAME):$(ERRATA_LEVEL)

.PHONY: image

image: Dockerfile
	docker build \
		--build-arg UCS_BASE=$(UCS_BASE) \
		--build-arg UCS_TARGET=$(UCS_TARGET) \
		--build-arg ERRATA_LEVEL=$(ERRATA_LEVEL) \
		--tag "$(TARGET_TAG)" .
	docker tag "$(TARGET_TAG)" "$(IMAGE_NAME):latest"
