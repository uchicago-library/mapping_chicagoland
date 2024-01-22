/*!
 * IE10 viewport hack for Surface/desktop Windows 8 bug
 * Copyright 2014-2015 Twitter, Inc.
 * Licensed under MIT (https://github.com/twbs/bootstrap/blob/master/LICENSE)
 */

// See the Getting Started docs for more information:
// http://getbootstrap.com/getting-started/#support-ie10-width

(function () {
  'use strict';

  if (navigator.userAgent.match(/IEMobile\/10\.0/)) {
    var msViewportStyle = document.createElement('style')
    msViewportStyle.appendChild(
      document.createTextNode(
        '@-ms-viewport{width:auto!important}'
      )
    )
    document.querySelector('head').appendChild(msViewportStyle)
  }

})();

$(document).ready(function () {
  $('[data-toggle="offcanvas"]').click(function () {
    $('.row-offcanvas').toggleClass('active')
  });
});
  $(document).ready(function(){
            var submitIcon = $('.searchbox-icon');
            var inputBox = $('.searchbox-input');
            var searchBox = $('.searchbox');
            var isOpen = false;
            submitIcon.click(function(){
                if(isOpen == false){
                    searchBox.addClass('searchbox-open');
                    inputBox.focus();
                    isOpen = true;
                } else {
                    searchBox.removeClass('searchbox-open');
                    inputBox.focusout();
                    isOpen = false;
                }
            });  
             submitIcon.mouseup(function(){
                    return false;
                });
            searchBox.mouseup(function(){
                    return false;
                });
            $(document).mouseup(function(){
                    if(isOpen == true){
                        $('.searchbox-icon').css('display','block');
                        submitIcon.click();
                    }
                });
        });
            function buttonUp(){
                var inputVal = $('.searchbox-input').val();
                inputVal = $.trim(inputVal).length;
                if( inputVal !== 0){
                    $('.searchbox-icon').css('display','block');
                } else {
                    $('.searchbox-input').val('');
                    $('.searchbox-icon').css('display','block');
                }
            }
var Tabs = {

  init: function() {
    this.bindUIfunctions();
    this.pageLoadCorrectTab();
  },

  bindUIfunctions: function() {

    // Delegation
    $(document)
      .on("click", ".transformer-tabs a[href^='#']:not('.active')", function(event) {
        Tabs.changeTab(this.hash);
        event.preventDefault();
      })
      .on("click", ".transformer-tabs a.active", function(event) {
        Tabs.toggleMobileMenu(event, this);
        event.preventDefault();
      });

  },

  changeTab: function(hash) {

    var anchor = $("[href='" + hash + "']");
    var div = $(hash);

    // activate correct anchor (visually)
    anchor.addClass("active").parent().siblings().find("a").removeClass("active");

    // activate correct div (visually)
    div.addClass("active").siblings().removeClass("active");

    // update URL, no history addition
    // You'd have this active in a real situation, but it causes issues in an <iframe> (like here on CodePen) in Firefox. So commenting out.
    // window.history.replaceState("", "", hash);

    // Close menu, in case mobile
    anchor.closest("ul").removeClass("open");

  },

  // If the page has a hash on load, go to that tab
  pageLoadCorrectTab: function() {
    this.changeTab(document.location.hash);
  },

  toggleMobileMenu: function(event, el) {
    $(el).closest("ul").toggleClass("open");
  }

}

Tabs.init();
//# sourceMappingURL=lib-main.js.map
