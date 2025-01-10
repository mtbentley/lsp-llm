# LLM LSP
A general purpose language server protocol server to provide basic LLM-assisted
coding.

Provides four actions on highlighted text:
1. `LLM Autocomplete`: takes a snippet of code (eg a function definition) and
   completes it
2. `LLM Instruct (Replace)`: takes a commented instruction followed by code
   snippet and follows the instruction to replace the highlighted code
3. `LLM Instruct (Append)`: takes a commented instruction followed by code
   snippet and follows the instruction to append more code. For example, use
   this to write tests for a function
4. `LLM Explain`: takes an optional commented question followed by highlighted
  code and explains the code or answers the question

A lot of this code is simplified from https://github.com/python-lsp/python-lsp-server

## TODO
In order of priority:
- [ ] Finish settings
- [ ] Clean up pythonic assumptions (ie, comments are assumed to be `#` and
      the prompt specifies python)
- [ ] add some instructions
- [ ] tests
- [ ] screen recording for readme
- [ ] I think some models support special sequences to separate code from other
      parts? Look into that
- [ ] improve prompts
- [ ] support adding more context
