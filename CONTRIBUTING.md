Thanks for your interest in contributing to this Doosan robot arm automation project.  
Contributions in the form of bug reports, feature requests, documentation improvements and code changes are all welcome.

## How to get started

Fork this repository to your own GitHub account.  
Create a new branch for your change:
   git checkout -b feature/my-new-feature
Make your changes in that branch.

Test your changes on a safe setup (simulation or low‑speed robot cell) before opening a pull request.
Open a pull request (PR) with a clear description of what you changed and why.
If you are unsure whether an idea fits the project, you can start by opening an issue to discuss it first.

Reporting bugs
When reporting a bug, please include:
  Clear description of the problem
  Steps to reproduce (commands, robot state, program name)
  Expected vs. actual behavior
  Robot model, controller software version and relevant configuration details
  If possible, add minimal example code or configuration that shows the issue.

Suggesting enhancements
Enhancement suggestions are welcome.
In your issue or pull request, describe:
  The current limitation or problem
  The behavior or feature you would like to see
  Any constraints related to safety, cycle time or hardware
  If your suggestion affects existing users, explain the impact and potential migration path.

Code style and structure
To keep the project consistent and maintainable:
  Follow the existing file and folder structure when adding new programs or scripts.
  Use clear, descriptive names for programs, functions and variables (e.g. main_pick_place, safe_move_home).
  Add short comments where behavior is not obvious (especially safety‑related logic).
  Keep changes focused: one logical change per branch/PR if possible.
  If a style guide is added later (for example for DRL or Python), please follow that guide.

Testing your changes
Before opening a PR:
  Verify that scripts load without errors in the Doosan environment.
  Test motions in simulation or at reduced speed in the real cell, respecting all safety procedures from the official Doosan manuals.
  Ensure that existing programs still run as expected if your change touches shared code.
  Describe which tests you ran in your pull request description.

Safety and responsibility
This project involves industrial robot hardware.
By contributing, you agree to:
  Always follow the official Doosan installation, programming and safety manuals when running any code from this repository.
  Never bypass or disable safety systems in order to test code.
  Clearly document any behavior that can affect safety (high speeds, collaborative vs. industrial modes, external safety devices).
  Unsafe changes may be rejected or requested to be revised.

Licensing and legal
By submitting a contribution:
  You confirm that you are authorized to contribute the code or documentation.
  You agree that your contribution will be provided under the same license as this repository (see LICENSE once added).
  If you are contributing on behalf of a company, ensure that your internal policies allow open collaboration.

Questions and support
If you have questions about contributing:
  Open an issue with the label question or discussion.

Or contact the maintainer(s) listed in the README’s Contact section.

Thank you for helping improve this project!
