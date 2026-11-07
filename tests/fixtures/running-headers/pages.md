FrontBeforeHeading starts here, before any top-level heading.

\clearpage

FrontContinuation is still before the first heading.

\clearpage
@MAIN@

# @FIRST@

OpeningFirst starts the first top-level division.

\clearpage

BodyFirstOdd is a normal body page in the first division.

## SubordinateHeading

A subordinate heading must not replace the current chapter.

\clearpage

BodyFirstEven is another normal body page in the first division.

\clearpage
\thispagestyle{empty}
\null
\clearpage

# @SECOND@ {.unnumbered}

OpeningSecond starts an unnumbered top-level division.

\clearpage

BodySecondOdd is a normal body page in the second division.

## AnotherSubordinate

The unnumbered division remains current after a subordinate heading.

\clearpage

BodySecondEven is another normal body page in the second division.
