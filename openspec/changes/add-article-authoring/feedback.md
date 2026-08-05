
 - There should be a preview button on
 - Should be possible to go to edit from the view page (if you have sufficient rights) rather than having to go to the article listing and click edit
 - The project page should show articles as the main tab if there are any rather than description

 - The hero image as the preview thing is a challenge. What dimensions do we want to support here? Perhaps it needs to be that the user uploads the image and are presented with a dialog where they can move the image around to the part they care about (for the hero section). This should then stay the same ratio as the screen size changes rather than what happens at the moment that more image is revealed as the screen shrinks in size.
    - Then on the preview card, they should be able to do the same to select a different portion/resize of the image


## Email sending

There are discrepancies with the current broadcast email approaach.

I don't want to start giving people more work - having to click the link in an email that only has one article in it is annoying.

At the same time, we don't want to be flooding people's inboxes with articles that they are following. Or what? Maybe that's fine?

Suggestion to have articles go direct to inbox. No coalescing. Users can unfollow if they don't want it.

Requires us to build some mjml pipeline for the documents

Also want to make it clear that these aren't from Naglasupan project itself (except when they are ;)) - ie have the project and author included in the email.




- The hero image on an article has a few representations:
 - a) When editing the artilcle page
 - b) when viewing the full article page
 - c) when viewing the list of articles and it's the main article listed
 - d) when viewing the list of articles and it's a non-main sub article listed
 - e) all of the above on smaller screens

Problems:
  - a + b should be the same, they are not at the moment.
  - Are c and d the same or are they different dimensions
  - I want the image to scale proportionally with any screen resizing so that it remains the same (scaled) shape for the a+b case regardless of viewing portal, and likewise for c+d
  - On image upload, the user should be presented with a dialog to select which part of the image they want to be in the main hero section - allowing the user to crop/pan to select the right area they're after.
  - On the preview card they should be able to do the same to select a different portion of the uploaded image.

 loads as the preview thing is a challenge. What dimensions do we want to support here? Perhaps it needs to be that the user uploads the image and are presented with a dialog where they can move the image around to the part they care about (for the hero section). This should then stay the same ratio as the screen size changes rather than what happens at the moment that more image is revealed as the screen shrinks in size.
    - Then on the preview card, they should be able to do the same to select a different portion/resize of the image

Done:

- The select image dialog that appears from the library is ugly
- If we're going to select large wide images to represent the article, we should have the list of displaying articles be better at rendering those images. Right now it shows it as truncated icon.
- Hero image doesn't get removed - click remove and save and it remains
