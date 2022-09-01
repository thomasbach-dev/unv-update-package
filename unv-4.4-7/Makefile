UCS_BASE := 4.4-6
UCS_TARGET := 4.4-7
ERRATA_LEVEL := 985

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
