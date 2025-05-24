## General

These cadastre files describe the administrative boundaries of regions in Indonesia. The level 3 subdivisions are used. The level 1 subdivisions can be viewed in the browser [here](https://gadm.org/maps/IDN_1.html).

The project's area of focus Bandung Regency, lies in Indonesia, Java, Jawa Barat (L1; 28; [link](https://gadm.org/maps/IDN/jawabarat_2.html)), and more specifically Bandung regency/kabupaten (L2; 18; [link](https://gadm.org/maps/IDN/jawabarat/bandung.html)).

The version 4.1 files were downloaded from: https://gadm.org/download_country.html.

## Filtered

We focus on Java. See `gadm_java.py`. `NAME_1`:
- Banten (27)
- Jakarta Raya (26)
- Jawa Barat (28)
- Jawa Tengah (29)
- Jawa Timur (30)
- Yogyakarta (31)

## GADM and DIBI hierarchies

The text below aims to aid understanding of the GADM and DIBI hierarchies and their identifiers. If you want to learn more, then check out the links above, or open the `cadastre/gadm41_IDK_3_Java.shp` file in GIS software (e.g., QGIS) and inspect the entries contained in the file (e.g., open an attribute table). Note: the numbers used in the [online GADM maps](https://gadm.org/maps/IDN_1.html) seem to differ from those in the `.shp` files.

The DIBI regions can differ slightly in naming and in which areas are used. This is why in the code we perform mapping from GADM ids to DIBI ids. Check out the `dibi_provinces.md` file and the `dibi_.py` files for more information.

```
Standard    : IND -> Jawa Barat -> Bandung                        -> Pangalengan
Level       :        Province      Kabupaten / regency / district    Subdistrict
GADM lvl    : 0      1             2                                 3 
GADM id .shp: IDN    9             2                                 25
GADM l3 id  : IDN.9.2.25_1. Ids always end with _1.
```
