# The testing language

The test language is an s-expression-like language where the
each list is a function call with the call first and the arguments (if any)
are later (ie. prefix notation).  The expression will result in a true or false 
value that determines whether the test has passed or not.

For example, the YAML-encoded expression
```
[any, [mime], text/plain, application/json]
```
might be represented in a normal programming language as:
```
any(mime(), 'text/plain', 'application/json')
```
which would return true if the subject file's mime type was one of
text/plain or application/json


## data types
everything is considered to be a native data type, unless it is coerced by
a function.  For example, boolean functions will coerce their
arguments to booleans.  Comparison functions (such as 'eq') will coerce all of 
the arguments to match the type of the first argument.

## Boolean functions
The boolean functions are:
| function | args | operation |
| -------- | ---- | --------- |
| true     | none | always returns true |
| false    | none | always returns false |
| and      | 2+   | returns true when all are true |
| or       | 2+   | returns true when any are true  |
| not      | 1    | returns the inverse of the logic |

## Comparison
The comparison functions are as follows:
| function | operation            |
| -------- | ---------            |
| eq       | Equality             |
| ne       | Inequality           |
| lt       | Less than            |
| le       | Less than or equal   |
| gt       | Greater than         |
| ge       | Greater than or equal |

Each take two arguments.  The data type for the arguments will be coerced to 
the data type of the first argument.

## Other comparisons
Other comparison functions

| function | args | operation |
| -------- | ---- | --------- |
| any      | 2+   | return true if first appears in any of the rest of args |
| re       | 2    | return true if the 1st arg regex matches the 2nd arg |

## Data functions
| function | args | operation |
| -------- | ---- | --------- |
| size     | none | returns the size of the subject file |
| mime     | none | returns the mime type of the subject file |
| json     | 1    | parses the subject file as json and returns the value at the path |
| xpath    | 1, 2    | parses the subject file as xml and returns the value at xpath in arg1. If arg2 is provided, return that attribute instead of text |
| media    | 1    | parses the subject file via media info and returns the value at the path |
| data     | none | returns the raw file data|
| contains | 2+   | returns true if the first argument contains the later argument strings |
| int      | 1    | coerce to integer |
| str      | 1    | coerce to string |
| bool     | 1    | coerce to boolean |
| float    | 1    | coerce to float |
| lower    | 1    | force the arg to lower case |
| len      | 1    | return the integer length of the arg |
| haskey   | 2    | return true if the data structure in arg1 has the key arg2 |
| csv      | 0+   | return the 2d CSV structure if no arguments, the given row if 2 args, and the row/column value if 3 args |
