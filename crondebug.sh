#!/bin/bash
echo "PATH: $PATH" >> /root/caner/debug.log
which uv >> /root/caner/debug.log 2>&1
echo "whoami: $(whoami)" >> /root/caner/debug.log
