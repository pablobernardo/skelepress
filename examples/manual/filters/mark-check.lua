-- Consumer-owned, opt-in instruction marker; ordinary spans are untouched.
function Span(span)
  if not span.classes:includes("operator-check") then
    return nil
  end
  table.insert(span.content, 1, pandoc.Space())
  table.insert(span.content, 1, pandoc.Strong({pandoc.Str("CHECK:")}))
  return span
end
