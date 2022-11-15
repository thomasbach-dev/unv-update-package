UCS_BASE := 4.4-9
UCS_BASE_ERRATA := 1333
UCS_TARGET := $(UCS_BASE)-vbm
ERRATA_LEVEL := $(UCS_BASE_ERRATA)

IMAGE_NAME := unv-$(UCS_TARGET)
TARGET_TAG := $(IMAGE_NAME):$(ERRATA_LEVEL)

.PHONY: image

image: build.sh Dockerfile
	docker build \
		--build-arg UCS_BASE=$(UCS_BASE) \
		--build-arg UCS_BASE_ERRATA=$(UCS_BASE_ERRATA) \
		--tag "$(TARGET_TAG)" .
	docker tag "$(TARGET_TAG)" "$(IMAGE_NAME):latest"

build.sh:
	ln -f ../build.sh
