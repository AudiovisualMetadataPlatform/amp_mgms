# ina-speech-tools-singularity
INA Speech Tools in a Singularity Container for AMP

To build:
```
time singularity build --fakeroot ina-speech-tools-singularity.sif Singularity.recipe
```

To run:
```
./ina-speech-tools-singularity.sif <audio file>  <output json>
```

Both the audio file and the output file should be either in the user's home directory or /tmp.  Other options can be handled by using run-time binding.
