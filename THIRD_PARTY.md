# Licensing and asset provenance

Toddler OS application source, original SVGs and project-authored content are
offered under GPL-3.0-only, with the full text in LICENSE. The project-generated
illustrations and recordings are distributed under the same terms to the extent
the project owner can grant those rights. This does not change third-party
licences or claim exclusive copyright in AI output.

| Component | Provenance / terms |
| --- | --- |
| Andika Regular | SIL International; SIL Open Font License 1.1. The font and required notice are in `app/static/fonts/`. [Upstream](https://github.com/google/fonts/tree/main/ofl/andika). |
| Piper speech engine | Optional dependency, not vendored. [Piper source and GPLv3 licence](https://github.com/OHF-Voice/piper1-gpl). Other installed Python packages retain their own licences. |
| Cori high British English voice | Optional external download, not bundled. [Model card](https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_GB/cori/high/MODEL_CARD) describes a LibriVox public-domain training dataset. This is a statement about the dataset, not a separate explicit weight-licence grant. Review upstream terms for your use or redistribution. The downloader pins file hashes. |
| Bundled maths and storybook audio | Synthesised locally using the Cori voice and project-authored text for The Space Cat and Luciana and Dad. Builders and text/hash/timing manifests are supplied, including the name pronunciation. No school phonics recordings are included. |
| Ninja and storybook PNG illustrations | Made using OpenAI image generation, including The Space Cat and Luciana and Dad. Sanitised prompt manifests are supplied alongside the assets. Ninja art used a supplied fantasy character image as visual direction; that reference image is not included. |
| Icons, wallpapers and dojo SVG | Original project-authored SVG artwork, distributed with its source. |
| Book Dash books and illustrations | Come Back, Cat! and Where’s That Cat?, CC BY 4.0. Original images are preserved byte-for-byte. Original reading/wordless editions and separately labelled typed-choice adaptations are included. See [full creator credits and changes](app/static/storybooks/bookdash/CREDITS.txt), [source hashes](app/static/storybooks/bookdash/download-manifest.json) and [licence](app/static/storybooks/bookdash/CC-BY-4.0.txt). |

Book Dash content and the new adaptations/narration retain CC BY 4.0; they are
not relicensed as GPL. The publisher's logo appears with each edition's credits.

The project does not bundle the optional voice model, Python package binaries,
privately licensed phonics packs, personal writing, saved books or user databases.
If you add external assets, record their source and licence before contributing
them. Do not infer permission to redistribute from a free download button.

Read Write Inc. is a third-party reading programme. The default letter order
references [Oxford Owl's public parent guidance](https://home.oxfordowl.co.uk/reading/reading-schemes-oxford-levels/read-write-inc-phonics-guide/).
No official recordings, logos or endorsement are included.
