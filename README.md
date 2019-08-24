# Icewind Dale Container Sorter

A Python 3 script to sort all containers in an area of Icewind Dale by their resource references.

Most useful for item hoarders.

```bash
# Assuming you want to sort BALDUR.SAV, this line sorts all containers in area 2115.
python3 main.py BALDUR.SAV --area AR2115.are --sort
# Then just copy OUTPUT.SAV over the old SAV file. 
```

I wrote this from scratch because NearInfinity wasn't quite working for me and I don't think it supports container sorting yet.
