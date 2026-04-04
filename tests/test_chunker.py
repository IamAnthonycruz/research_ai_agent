from research_agent.RAG.chunk import Chunk
def test_short_paragraph_chunk():
    short_text = "The Federal Reserve held interest rates steady at its latest meeting. Chair Powell noted that inflation remains above the two percent target but acknowledged recent progress. Markets responded positively to the announcement."
    result = Chunk.chunk_note(short_text, "https://test.com","mytest.comtitle")
    assert len(result) == 1
def test_long_paragraph_chunk():
    text= """The history of nuclear fusion research spans more than seven decades. Scientists first achieved fusion reactions in laboratory settings during the 1950s. The basic principle involves forcing light atomic nuclei together to form heavier ones, releasing enormous energy in the process. This is the same reaction that powers the sun and all stars.
Early experiments focused on magnetic confinement, using powerful magnetic fields to contain superheated plasma. The tokamak design, originally developed in the Soviet Union, became the dominant approach by the 1970s. Researchers found that maintaining stable plasma at temperatures exceeding one hundred million degrees Celsius presented extraordinary engineering challenges. The plasma tends to develop instabilities that cause it to touch the walls of the containment vessel, cooling rapidly and ending the reaction.
Inertial confinement represents the other major approach. Instead of holding plasma in place with magnets, this method uses powerful lasers to compress a tiny fuel pellet so quickly that fusion occurs before the material can fly apart. The National Ignition Facility in California achieved a breakthrough in December 2022 when its lasers produced more energy from fusion than they delivered to the target. This milestone, while scientifically significant, required far more total energy to operate the lasers than the fusion reaction produced.
Private companies have entered the field with substantial venture capital funding. Commonwealth Fusion Systems, a spinoff from MIT, is developing compact tokamaks using high-temperature superconducting magnets. TAE Technologies has pursued a different plasma confinement geometry. Helion Energy has attracted attention and investment from prominent technology figures. These companies promise faster timelines than government-funded projects, though skeptics note that fusion has consistently failed to meet optimistic projections throughout its history.
Government funding continues to play a central role. The International Thermonuclear Experimental Reactor, known as ITER, is under construction in southern France. This massive international collaboration aims to demonstrate that fusion can produce net energy at scale. The project has faced significant delays and cost overruns, with the current estimated completion date pushed well into the 2030s. Despite these challenges, ITER remains the largest and most ambitious fusion experiment ever attempted."""
    result = Chunk.chunk_note(text, "https://test.com", "test-title")
    assert len(result) > 1
def test_empty_paragraph_chunk():
    text = ""
    result = Chunk.chunk_note(text, "https://test.com", "test-title")
    assert len(result) == 0