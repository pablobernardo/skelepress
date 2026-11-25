-- Defer image work to the moment the browser regains interest in it.
--
-- HTML only. `loading="lazy"` tells the browser not to fetch an image until
-- it approaches the viewport, and to keep it in memory afterwards; embedded
-- data URIs are inert for loading but remote URLs and any future referenced-
-- asset mode still benefit. `decoding="async"` keeps decoding off the main
-- thread. Other formats keep their output unchanged.
--
-- Output is identical when the document has no images.

function Image(image)
  if FORMAT ~= "html" then
    return nil
  end
  image.attributes["loading"] = "lazy"
  image.attributes["decoding"] = "async"
  return image
end
