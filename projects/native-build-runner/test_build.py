from build import all_targets, clean, DIST


def test_all_targets_creates_manifest() -> None:
    all_targets()
    assert (DIST / "manifest.json").exists()
    clean()


if __name__ == "__main__":
    test_all_targets_creates_manifest()
    print("ok")

