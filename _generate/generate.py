import inflection
import base64
import requests
import json
import glob

BASE_URL = "https://google-webfonts-helper.herokuapp.com/api"

TEMPLATE = """
@font-face {
  font-family: '{family}';
  font-style: {style};
  font-weight: {weight};
  src: {src};
}
"""

session = requests.Session()

def camelize(name):
    return inflection.camelize(name.replace("-", "_"))

r = session.get(BASE_URL + "/fonts")
r.raise_for_status()

for font in r.json():
    font_id = font["id"]
    path = font_id.replace("-", "_")
    name = inflection.camelize(path)

    for metadata_file in glob.glob("fonts/*/%s/METADATA.pb" % font_id.replace("-", "")):
        with open(metadata_file, "rb") as f:
            metadata = f.read()
        break
    else:
        print "Unable to load metadata for %s" % font_id
        continue

    with open(path + ".gen.go", "wb") as f:
        print name

        f.write("package fonts\n\n")

        f.write("\n".join(
            "// " + line
            for line in metadata.strip().split("\n")
        ))
        f.write("\n\n")

        r = session.get(BASE_URL + "/fonts/%s" % font["id"])
        r.raise_for_status()

        data = r.json()
        for variant in data["variants"]:
            variant_name = camelize(variant["id"])

            src = []
            for local in variant["local"]:
                src.append("local('%s')" % local)

            font_resp = session.get(variant["woff2"])

            src.append(
                "url('data:font/woff2;base64,%s') format('woff2')" % (
                    base64.b64encode(font_resp.content),
                ),
            )

            data = [
                "@font-face {",
                "font-family: {};".format(variant["fontFamily"]),
                "font-style: {};".format(variant["fontStyle"]),
                "font-weight: {};".format(variant["fontWeight"]),
                "src: {};".format(", ".join(src)),
                "}",
            ]

            f.write(
                "const %s = `%s`;\n" % (name + variant_name, " ".join(data)),
            )
