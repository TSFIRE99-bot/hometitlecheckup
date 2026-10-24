from titlecheck.demo import DEMO, DEMO_NEIGHBORS
from titlecheck.geo import analyze
from titlecheck.parcel_map import START, build_map, explore_map


def render(demo):
    shape, neighbors = analyze(DEMO.rings, {p.parcel_id: p.rings for p in DEMO_NEIGHBORS})
    return build_map(DEMO, DEMO_NEIGHBORS, neighbors, shape, demo=demo).get_root().render()


def test_real_homes_get_property_lines_over_the_satellite_photo():
    html = render(demo=False)
    assert "World_Imagery" in html and "World_Transportation" in html
    assert "1236 SAMPLE ST (demo)" in html and "Neighbor: Right" in html


def test_demo_block_never_shows_a_real_place():
    html = render(demo=True)
    assert "World_Imagery" not in html and "openstreetmap" not in html.lower().replace("openstreetmap contributors", "")


def test_property_map_page_has_real_map_layers():
    html = explore_map(START, 17).get_root().render()
    for layer in ("World_Imagery", "openstreetmap", "World_Transportation", "World_Boundaries_and_Places"):
        assert layer in html
