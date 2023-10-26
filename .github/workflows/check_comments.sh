#!/bin/bash

COMMENT_LINES=0
TOTAL_LINES=0

for file in $(git diff --name-only HEAD~1); do
    # Detect file type
    case $file in
        *.js)
            # For JavaScript, single-line comments start with //
            # Block comments are between /* and */
            COMMENT_LINES_FILE=$(grep -E '^\s*//|^\s*/\*|\*/' $file | wc -l)
        ;;
        *.py)
            # For Python, comments start with #
            COMMENT_LINES_FILE=$(grep -E '^\s*#' $file | wc -l)
        ;;
        *Dockerfile)
            # For Dockerfiles, comments start with #
            COMMENT_LINES_FILE=$(grep -E '^\s*#' $file | wc -l)
        ;;
        *)
            # Skip other files
            continue
        ;;
    esac
    
    TOTAL_LINES_FILE=$(wc -l < $file)
    
    COMMENT_LINES=$(($COMMENT_LINES + $COMMENT_LINES_FILE))
    TOTAL_LINES=$(($TOTAL_LINES + $TOTAL_LINES_FILE))
done

PERCENTAGE=$(awk "BEGIN { pc=100*${COMMENT_LINES}/${TOTAL_LINES}; i=int(pc); print (pc-i<0.5)?i:i+1 }")

if (( $PERCENTAGE < 10 )); then
    echo "Failed: Comment percentage is less than 10%"
    exit 1
else
    echo "Passed: Comment percentage is 10% or more"
fi
