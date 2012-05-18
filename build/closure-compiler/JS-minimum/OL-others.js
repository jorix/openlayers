// ** From externs/es5.js **
// Used in: Format/JSON.js
    /**
     * @see https://developer.mozilla.org/En/Using_native_JSON
     */
    Window.prototype.JSON = {};

    /**
     * @param {*} value
     * @param {(Array.<string>|(function(string, *) : *)|null)=} opt_replacer
     * @param {(number|string)=} opt_space
     * @return {string}
     * @see http://ejohn.org/blog/ecmascript-5-strict-mode-json-and-more/
     */
    Window.prototype.JSON.stringify =
        function(value, opt_replacer, opt_space) {};

// ** From externs/ie_css.js **
// Used in: Renderer/VML.js
    /**
     * @param {string} bstrSelector
     * @param {string} bstrStyle
     * @param {number=} opt_iIndex
     * @return {number}
     * @see http://msdn.microsoft.com/en-us/library/aa358796%28v=vs.85%29.aspx
     */
    StyleSheet.prototype.addRule;

// ** From externs/deprecated.js **
// Used in: Request/XMLHttpRequest.js
    var opera;

