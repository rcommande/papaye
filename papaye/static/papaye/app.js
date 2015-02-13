'use strict';

var papaye = angular.module('papaye', ['ngRoute', 'ngResource'])

.config(['$routeProvider', function($routeProvider) {

    var isConnected = function(restricted) {
        return function($q, $timeout, $http, $location, login) {
            var deferred = $q.defer(),
                url = $location.$$url,
                username = "";

            deferred.promise.then(function(){
                console.log('then');
                console.log(username);
                login.setUsername(username);
            });

            $http.get('/islogged', {responseType: 'json'}).success(function(data, status, headers, config) {
                username = data;
                $timeout(deferred.resolve, 0);
            })
            .error(function(data, status, headers, config) {
                console.log('error');
                login.setUsername(username);
                if (status == 401) {
                    if (restricted === true) {
                        var redirectUrl = '/login';
                        if (url !== '/') {
                            redirectUrl = redirectUrl + '/' + url.slice(1).replace('/', '-');
                        }
                        $location.url(redirectUrl);
                    }
                }
                else {
                    noty({text: 'An error has occurred', type: "error", layout: "bottom", timeout: 5000});
                }
            });
            return (restricted === false) ? true: deferred.promise;
        };
    }
    $routeProvider.when('/', {
        templateUrl: 'static/papaye/partials/index.html',
        controller: 'HomeController',
        resolve: {
            connected: isConnected(false)
        }
    })
    $routeProvider.when('/browse', {
        templateUrl: 'static/papaye/partials/list_packages.html',
        controller: 'ListPackageController',
        resolve: {
            connected: isConnected(true)
        }
    })
    $routeProvider.when('/login', {
        templateUrl: 'static/papaye/partials/login.html',
        controller: 'LoginController',
    })
    $routeProvider.when('/login/:to', {
        templateUrl: 'static/papaye/partials/login.html',
        controller: 'LoginController',
    })
    .when('/browse/:name', {
        templateUrl: 'static/papaye/partials/package.html',
        controller: 'SinglePackageController',
        resolve: {
            connected: isConnected(true)
        }
    })
    .when('/browse/:name/:version', {
        templateUrl: 'static/papaye/partials/package.html',
        controller: 'SinglePackageController',
        resolve: {
            connected: isConnected(true)
        }
    })
    .when('/reload/:url', {
        templateUrl: 'static/papaye/partials/empty.html',
        controller: 'ReloaderController',
    })
    .otherwise({
        redirectTo: '/'
    });
}
]);
