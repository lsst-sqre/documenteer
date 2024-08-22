#########################################
Editing a technote with the GitHub web UI
#########################################

For small edits, you can edit a technote directly from GitHub's website.
The benefit of this approach is that you don't need to clone a repository or install any software to contribute to a Rubin technote.
You can even get a branch-based preview of your changes by creating a pull request.
The downside is that you only get feedback on the build status and linter after you've committed your changes.

Using the edit-on-github feature
--------------------------------

You can edit a technote directly on GitHub's website.
You can make a single commit directly from GitHub's website.
To open this interface, either:

- Navigate to the :file:`index.rst` or :file:`index.md` file on the technote's GitHub page and press the :kbd:`e` key (alternatively click the pencil icon in the top right corner of the file view).
- From the technote's pubilshed page, click the :guilabel:`Edit on GitHub` link on the left sidebar, under the :guilabel:`Source` heading.

Make your edits and end a commit message.
It's recommended to commit to a new branch so that you can preview your changes in a pull request before merging them.

For more details on this feature, see GitHub's `documentation on Editing files <https://docs.github.com/en/repositories/working-with-files/managing-files/editing-files>`__.

Using github.dev
----------------

An alternative approach is to use the `github.dev <https://github.dev>`__ service.
Open the technote's GitHub page in your browser and press the :kbd:`.` key.
This opens a basic VS Code editor in your browser.
You can edit multiple files and commit your changes directly from the browser.

For more details on this feature, see GitHub's `documentation on github.dev <https://docs.github.com/en/codespaces/the-githubdev-web-based-editor>`__.
