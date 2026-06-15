"""Declarative list of the 12 knowledge-base sources to scrape.

Each :class:`Source` pairs a stable attraction id with the official URL to scrape
and static metadata that the extractor/transformer cannot reliably derive from
page content (category, canonical title, the persona-agnostic nudge).
"""

from __future__ import annotations

from pydantic import BaseModel


class Source(BaseModel):
    """A single scrape target for the ETL pipeline."""

    attraction_id: str
    title: str
    category: str
    url: str
    nudge: str


SOURCES: list[Source] = [
    Source(
        attraction_id="zayed_mosque",
        title="Sheikh Zayed Grand Mosque",
        category="Religious Landmark",
        url="https://www.szgmc.gov.ae/en/",
        nudge="Plan around prayer times and dress modestly — then continue to the "
        "Wahat Al Karama memorial nearby.",
    ),
    Source(
        attraction_id="louvre",
        title="Louvre Abu Dhabi",
        category="Museum",
        url="https://www.louvreabudhabi.ae/en",
        nudge="Pair your visit with neighbouring Saadiyat Cultural District museums "
        "for a full day of art.",
    ),
    Source(
        attraction_id="qasr_al_watan",
        title="Qasr Al Watan",
        category="Palace",
        url="https://www.qasralwatan.ae/en",
        nudge="Stay for the evening 'Palace in Motion' light show projected onto the "
        "facade.",
    ),
    Source(
        attraction_id="yas_island",
        title="Yas Island",
        category="Entertainment District",
        url="https://www.yasisland.com/en",
        nudge="Bundle theme-park tickets in advance and use the free Yas Express "
        "shuttle between parks.",
    ),
    Source(
        attraction_id="saadiyat_beach",
        title="Saadiyat Public Beach",
        category="Beach",
        url="https://www.saadiyat.ae/en",
        nudge="Arrive early for parking and look out for nesting hawksbill turtles in "
        "season.",
    ),
    Source(
        attraction_id="corniche",
        title="Abu Dhabi Corniche",
        category="Waterfront",
        url="https://visitabudhabi.ae/en/where-to-go/regions/abu-dhabi-city",
        nudge="Rent a bike along the cycle path and finish with sunset views over the "
        "skyline.",
    ),
    Source(
        attraction_id="qasr_al_hosn",
        title="Qasr Al Hosn",
        category="Historic Fort",
        url="https://www.dctabudhabi.ae/en/things-to-do/qasr-al-hosn",
        nudge="Combine with the adjacent House of Artisans to see traditional Emirati "
        "crafts.",
    ),
    Source(
        attraction_id="heritage_village",
        title="Heritage Village",
        category="Cultural Site",
        url="https://visitabudhabi.ae/en/things-to-do/culture/heritage/heritage-village",
        nudge="Visit the workshops to watch metalwork and pottery, then enjoy the "
        "breakwater views back toward the city.",
    ),
    Source(
        attraction_id="airport_transfer",
        title="Zayed International Airport Transfers",
        category="Transport",
        url="https://www.zayedinternationalairport.ae/en",
        nudge="Pre-book an airport taxi or check the A1 express bus timings before you "
        "land.",
    ),
    Source(
        attraction_id="public_transport",
        title="Abu Dhabi Public Transport",
        category="Transport",
        url="https://admobility.gov.ae/en/pb-bus-service",
        nudge="Pick up a Hafilat card for buses and keep it topped up for seamless "
        "travel across the city.",
    ),
    Source(
        attraction_id="visa_info",
        title="UAE Tourist Visa Information",
        category="Travel Essentials",
        url="https://u.ae/en/information-and-services/visa-and-emirates-id",
        nudge="Confirm whether your nationality qualifies for visa-on-arrival before "
        "booking your trip.",
    ),
    Source(
        attraction_id="culture_etiquette",
        title="Culture & Etiquette in Abu Dhabi",
        category="Travel Essentials",
        url="https://u.ae/en/information-and-services/visiting-and-exploring-the-uae/social-responsibility",
        nudge="Dress modestly at religious and government sites and ask before "
        "photographing people.",
    ),
]

# Stable mapping for quick lookups by id.
SOURCES_BY_ID: dict[str, Source] = {s.attraction_id: s for s in SOURCES}
