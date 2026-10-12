# PlantVillage dataset

LeafCheck is fine-tuned on the **PlantVillage** image corpus (the "color" split).

## What it is

A labelled image collection of plant leaves photographed against a uniform grey background under controlled lighting. Used as a benchmark for plant-disease classification research since 2016.

- 54,303 images
- 14 crop species
- 26 disease + healthy classes

LeafCheck uses only the **19 classes** that fall within the four crops we support:

| Crop        | # classes | Conditions                                                    |
| ----------- | --------- | ------------------------------------------------------------- |
| Tomato      | 10        | bacterial spot, early blight, late blight, leaf mold, septoria leaf spot, spider mites (two-spotted spider mite damage), target spot, yellow leaf curl virus, mosaic virus, healthy |
| Potato      | 3         | early blight, late blight, healthy                            |
| Corn (maize)| 4         | cercospora / gray leaf spot, common rust, northern leaf blight, healthy |
| Bell pepper | 2         | bacterial spot, healthy                                       |

## License

PlantVillage is released under a **CC-BY-SA 3.0** license (Creative Commons Attribution-ShareAlike 3.0 Unported). The CC-BY-SA clause requires derivative works to be released under a compatible licence; LeafCheck is MIT-licensed, which the PlantVillage authors treat as compatible for non-commercial research use. If you redistribute LeafCheck weights, please keep the citation below and preserve the CC-BY-SA lineage acknowledgement.

## Citation

```bibtex
@article{geetharamani2019identification,
  title={Identification of plant leaf diseases using a nine-layer deep convolutional neural network},
  author={Geetharamani, G. and Pandian, J. Arun},
  journal={Computers \& Electrical Engineering},
  volume={78},
  pages={9--17},
  year={2019},
  publisher={Elsevier},
  doi={10.1016/j.compeleceng.2019.05.046}
}

@misc{hughes2015plantvillage,
  title={An open access repository of plant images for disease recognition},
  author={Hughes, David P. and Salath{\'e}, Marcel},
  year={2015},
  howpublished={GitHub repository},
  url={https://github.com/salathegroup/plantvillage}
}
```

## Where to get it

| Mirror | URL | Notes |
| ------ | --- | ----- |
| Mendeley (primary) | https://data.mendeley.com/datasets/tywbtsjrjv/1 | Requires free login to download. |
| Kaggle mirror     | https://www.kaggle.com/datasets/abdallahalidev/plantvillage-dataset | Requires free Kaggle login. |
| Salathe Lab GitHub| https://github.com/salathegroup/plantvillage | Crop-organised, no login. Some historical release labels. |

The LeafCheck data CLI accepts a **local folder** as `--source` because the public mirrors do not all allow direct programmatic download without credentials. Point `--source` at the unzipped PlantVillage colour subfolder to reproduce the documented 19-class split.

## Known limitations of the training data

- Photos are **lab-style**: leaf is centred, plain grey background, even lighting. Real field photos will look very different; the model will be less reliable on them.
- PlantVillage does **not** capture multiple diseases on one leaf, soil-borne diseases, or pest damage that isn't on the leaf surface.
- A handful of classes have **< 500 images**; the model is correspondingly noisier on them. Per-class precision/recall is listed in `reports/eval.md`.

## What is NOT in PlantVillage

PlantVillage does not contain any data on dosage, application equipment, integrated pest management, or treatment economics. LeafCheck's `data/advice.json` is sourced separately and is conservative by design (see README § Disclaimer).
