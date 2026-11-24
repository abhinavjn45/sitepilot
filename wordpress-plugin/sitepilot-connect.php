<?php
/**
 * Plugin Name: SitePilot
 * Description: Provides capability-protected read-only endpoints for SitePilot.
 * Version: 0.1.0
 * Requires at least: 7.1
 * Requires PHP: 8.2
 * Text Domain: sitepilot
 */

namespace SitePilot\Connect;

defined( 'ABSPATH' ) || exit;

/**
 * Registers read-only SitePilot REST endpoints.
 */
final class Plugin {
	private const PLUGIN_NAME    = 'SitePilot';
	private const PLUGIN_VERSION = '0.1.0';
	private const REST_NAMESPACE = 'sitepilot/v1';
	private const POST_STATUSES = array( 'publish', 'future', 'draft', 'pending', 'private' );
	private const DEFAULT_POSTS_PER_PAGE = 10;
	private const MAX_POSTS_PER_PAGE = 50;
	private const MAX_POST_PAGE = 10000;
	private const DEFAULT_USERS_PER_PAGE = 10;
	private const MAX_USERS_PER_PAGE = 50;
	private const MAX_USER_PAGE = 10000;
	private const DEFAULT_MEDIA_PER_PAGE = 10;
	private const MAX_MEDIA_PER_PAGE = 50;
	private const MAX_MEDIA_PAGE = 10000;
	private const COMMENT_STATUSES = array( 'approved', 'pending', 'spam', 'trash' );
	private const DEFAULT_COMMENTS_PER_PAGE = 10;
	private const MAX_COMMENTS_PER_PAGE = 50;
	private const MAX_COMMENT_PAGE = 10000;
	private const DEFAULT_CATEGORIES_PER_PAGE = 10;
	private const MAX_CATEGORIES_PER_PAGE = 50;
	private const MAX_CATEGORY_PAGE = 10000;
	private const DEFAULT_TAGS_PER_PAGE = 10;
	private const MAX_TAGS_PER_PAGE = 50;
	private const MAX_TAG_PAGE = 10000;

	/**
	 * Register the plugin's REST routes.
	 */
	public static function register_routes(): void {
		\register_rest_route(
			self::REST_NAMESPACE,
			'/status',
			array(
				'methods'             => \WP_REST_Server::READABLE,
				'callback'            => array( self::class, 'get_status' ),
				'permission_callback' => array( self::class, 'authorize_admin_request' ),
			)
		);

		\register_rest_route(
			self::REST_NAMESPACE,
			'/site-info',
			array(
				'methods'             => \WP_REST_Server::READABLE,
				'callback'            => array( self::class, 'get_site_info' ),
				'permission_callback' => array( self::class, 'authorize_admin_request' ),
			)
		);

		\register_rest_route(
			self::REST_NAMESPACE,
			'/plugins',
			array(
				'methods'             => \WP_REST_Server::READABLE,
				'callback'            => array( self::class, 'get_plugins' ),
				'permission_callback' => array( self::class, 'authorize_admin_request' ),
			)
		);

		\register_rest_route(
			self::REST_NAMESPACE,
			'/themes',
			array(
				'methods'             => \WP_REST_Server::READABLE,
				'callback'            => array( self::class, 'get_themes' ),
				'permission_callback' => array( self::class, 'authorize_admin_request' ),
			)
		);

		\register_rest_route(
			self::REST_NAMESPACE,
			'/posts',
			array(
				'methods'             => \WP_REST_Server::READABLE,
				'callback'            => array( self::class, 'get_posts' ),
				'permission_callback' => array( self::class, 'authorize_admin_request' ),
				'args'                => array(
					'page'     => array(
						'default'           => 1,
						'validate_callback' => array( self::class, 'validate_posts_page' ),
					),
					'per_page' => array(
						'default'           => self::DEFAULT_POSTS_PER_PAGE,
						'validate_callback' => array( self::class, 'validate_posts_per_page' ),
					),
					'status'   => array(
						'default'           => 'publish',
						'validate_callback' => array( self::class, 'validate_post_status' ),
					),
				),
			)
		);

		\register_rest_route(
			self::REST_NAMESPACE,
			'/pages',
			array(
				'methods'             => \WP_REST_Server::READABLE,
				'callback'            => array( self::class, 'get_pages' ),
				'permission_callback' => array( self::class, 'authorize_admin_request' ),
				'args'                => array(
					'page'     => array( 'default' => 1 ),
					'per_page' => array( 'default' => self::DEFAULT_POSTS_PER_PAGE ),
					'status'   => array( 'default' => 'publish' ),
				),
			)
		);

		\register_rest_route(
			self::REST_NAMESPACE,
			'/users',
			array(
				'methods'             => \WP_REST_Server::READABLE,
				'callback'            => array( self::class, 'get_users' ),
				'permission_callback' => array( self::class, 'authorize_admin_request' ),
				'args'                => array(
					'page'     => array( 'default' => 1 ),
					'per_page' => array( 'default' => self::DEFAULT_USERS_PER_PAGE ),
				),
			)
		);

		\register_rest_route(
			self::REST_NAMESPACE,
			'/media',
			array(
				'methods'             => \WP_REST_Server::READABLE,
				'callback'            => array( self::class, 'get_media' ),
				'permission_callback' => array( self::class, 'authorize_admin_request' ),
				'args'                => array(
					'page'     => array( 'default' => 1 ),
					'per_page' => array( 'default' => self::DEFAULT_MEDIA_PER_PAGE ),
				),
			)
		);

		\register_rest_route(
			self::REST_NAMESPACE,
			'/comments',
			array(
				'methods'             => \WP_REST_Server::READABLE,
				'callback'            => array( self::class, 'get_comments' ),
				'permission_callback' => array( self::class, 'authorize_admin_request' ),
				'args'                => array(
					'page'     => array( 'default' => 1 ),
					'per_page' => array( 'default' => self::DEFAULT_COMMENTS_PER_PAGE ),
					'status'   => array( 'default' => 'approved' ),
				),
			)
		);

		\register_rest_route(
			self::REST_NAMESPACE,
			'/categories',
			array(
				'methods'             => \WP_REST_Server::READABLE,
				'callback'            => array( self::class, 'get_categories' ),
				'permission_callback' => array( self::class, 'authorize_admin_request' ),
				'args'                => array(
					'page'     => array( 'default' => 1 ),
					'per_page' => array( 'default' => self::DEFAULT_CATEGORIES_PER_PAGE ),
				),
			)
		);

		\register_rest_route(
			self::REST_NAMESPACE,
			'/tags',
			array(
				'methods'             => \WP_REST_Server::READABLE,
				'callback'            => array( self::class, 'get_tags' ),
				'permission_callback' => array( self::class, 'authorize_admin_request' ),
				'args'                => array(
					'page'     => array( 'default' => 1 ),
					'per_page' => array( 'default' => self::DEFAULT_TAGS_PER_PAGE ),
				),
			)
		);
	}

	/**
	 * Require a WordPress user who can manage site options.
	 *
	 * @param \WP_REST_Request $request Current REST request.
	 * @return bool Whether the current user may read SitePilot endpoints.
	 */
	public static function authorize_admin_request( \WP_REST_Request $request ): bool {
		return \current_user_can( 'manage_options' );
	}

	/**
	 * Return non-sensitive runtime version information.
	 *
	 * @param \WP_REST_Request $request Current REST request.
	 * @return \WP_REST_Response Status response.
	 */
	public static function get_status( \WP_REST_Request $request ): \WP_REST_Response {
		return new \WP_REST_Response(
			array(
				'plugin_name'        => self::PLUGIN_NAME,
				'plugin_version'     => self::PLUGIN_VERSION,
				'wordpress_version'  => \get_bloginfo( 'version' ),
				'php_version'        => PHP_VERSION,
				'status'             => 'ok',
			),
			200
		);
	}

	/**
	 * Return allowlisted, non-sensitive WordPress site information.
	 *
	 * @param \WP_REST_Request $request Current REST request.
	 * @return \WP_REST_Response Site information response.
	 */
	public static function get_site_info( \WP_REST_Request $request ): \WP_REST_Response {
		$site_name        = \sanitize_text_field( \get_bloginfo( 'name', 'raw' ) );
		$site_description = \sanitize_textarea_field( \get_bloginfo( 'description', 'raw' ) );
		$home_url         = \esc_url_raw( \home_url( '/' ) );
		$site_url         = \esc_url_raw( \site_url( '/' ) );
		$wordpress_version = \sanitize_text_field( \get_bloginfo( 'version' ) );
		$php_version       = \sanitize_text_field( PHP_VERSION );
		$timezone         = \sanitize_text_field( (string) \get_option( 'timezone_string', '' ) );
		$locale           = \sanitize_text_field( \get_locale() );
		$raw_gmt_offset   = \get_option( 'gmt_offset' );
		$gmt_offset       = null;

		if ( \is_numeric( $raw_gmt_offset ) ) {
			$candidate_offset = (float) $raw_gmt_offset;
			if ( \is_finite( $candidate_offset ) && $candidate_offset >= -14 && $candidate_offset <= 14 ) {
				$gmt_offset = $candidate_offset;
			}
		}

		return new \WP_REST_Response(
			array(
				'site_name'        => '' !== $site_name ? $site_name : null,
				'site_description' => '' !== $site_description ? $site_description : null,
				'home_url'         => '' !== $home_url ? $home_url : null,
				'site_url'         => '' !== $site_url ? $site_url : null,
				'wordpress_version' => $wordpress_version,
				'php_version'       => $php_version,
				'timezone'          => '' !== $timezone ? $timezone : null,
				'gmt_offset'        => $gmt_offset,
				'locale'            => '' !== $locale ? $locale : null,
				'plugin_version'    => \sanitize_text_field( self::PLUGIN_VERSION ),
			),
			200
		);
	}

	/**
	 * Return allowlisted metadata for installed plugins.
	 *
	 * @param \WP_REST_Request $request Current REST request.
	 * @return \WP_REST_Response Plugin metadata response.
	 */
	public static function get_plugins( \WP_REST_Request $request ): \WP_REST_Response {
		if ( ! \function_exists( 'get_plugins' ) ) {
			require_once ABSPATH . 'wp-admin/includes/plugin.php';
		}

		$installed_plugins = \function_exists( 'get_plugins' ) ? \get_plugins() : array();
		$active_plugins    = \get_option( 'active_plugins', array() );
		$network_plugins   = \is_multisite() ? \get_site_option( 'active_sitewide_plugins', array() ) : array();
		$active_plugins    = \is_array( $active_plugins ) ? $active_plugins : array();
		$network_plugins   = \is_array( $network_plugins ) ? $network_plugins : array();
		$plugin_list       = array();

		if ( ! \is_array( $installed_plugins ) ) {
			$installed_plugins = array();
		}

		foreach ( $installed_plugins as $plugin_file => $metadata ) {
			if ( ! \is_string( $plugin_file ) ) {
				continue;
			}

			$plugin_file_is_safe = self::is_safe_plugin_file( $plugin_file );
			$plugin_metadata     = \is_array( $metadata ) ? $metadata : array();
			$is_active           = \in_array( $plugin_file, $active_plugins, true )
				|| \array_key_exists( $plugin_file, $network_plugins );

			$plugin_list[] = array(
				'plugin_file' => $plugin_file_is_safe ? $plugin_file : null,
				'name'        => self::nullable_plugin_text( $plugin_metadata['Name'] ?? null ),
				'version'     => self::nullable_plugin_text( $plugin_metadata['Version'] ?? null ),
				'status'      => $is_active ? 'active' : 'inactive',
				'description' => self::nullable_plugin_text( $plugin_metadata['Description'] ?? null, true ),
				'author'      => self::nullable_plugin_text( $plugin_metadata['Author'] ?? null ),
			);
		}

		return new \WP_REST_Response( array( 'plugins' => $plugin_list ), 200 );
	}

	/**
	 * Check that a plugin identifier is a safe relative WordPress plugin key.
	 *
	 * @param string $plugin_file Plugin file key from WordPress.
	 * @return bool Whether the key is safe to include in the response.
	 */
	private static function is_safe_plugin_file( string $plugin_file ): bool {
		if ( '' === $plugin_file || \strlen( $plugin_file ) > 512 ) {
			return false;
		}

		if ( 1 === \preg_match( '~[^A-Za-z0-9 _./-]~', $plugin_file ) ) {
			return false;
		}

		if ( '/' === $plugin_file[0] ) {
			return false;
		}

		foreach ( \explode( '/', $plugin_file ) as $segment ) {
			if ( '' === $segment || '.' === $segment || '..' === $segment ) {
				return false;
			}
		}

		return true;
	}

	/**
	 * Sanitize optional plugin metadata without coercing malformed values.
	 *
	 * @param mixed $value Plugin header value.
	 * @param bool  $multiline Whether line breaks should be preserved.
	 * @return string|null Sanitized value, or null when unavailable or malformed.
	 */
	private static function nullable_plugin_text( $value, bool $multiline = false ): ?string {
		if ( ! \is_string( $value ) ) {
			return null;
		}

		$sanitized = $multiline ? \sanitize_textarea_field( $value ) : \sanitize_text_field( $value );
		return '' !== $sanitized ? $sanitized : null;
	}

	/**
	 * Return allowlisted metadata for installed themes.
	 *
	 * @param \WP_REST_Request $request Current REST request.
	 * @return \WP_REST_Response Theme metadata response.
	 */
	public static function get_themes( \WP_REST_Request $request ): \WP_REST_Response {
		$installed_themes = \wp_get_themes();
		$active_stylesheet = \get_stylesheet();
		$theme_list        = array();

		if ( ! \is_array( $installed_themes ) ) {
			$installed_themes = array();
		}

		foreach ( $installed_themes as $stylesheet => $theme ) {
			if ( ! \is_string( $stylesheet ) && ! \is_int( $stylesheet ) ) {
				continue;
			}
			$stylesheet      = (string) $stylesheet;

			$is_theme_object = $theme instanceof \WP_Theme;
			$template        = $is_theme_object ? $theme->get_template() : null;
			$template        = \is_string( $template ) && $template !== $stylesheet
				&& self::is_safe_theme_identifier( $template )
				? $template
				: null;

			$theme_list[] = array(
				'stylesheet'   => self::is_safe_theme_identifier( $stylesheet ) ? $stylesheet : null,
				'name'         => $is_theme_object ? self::nullable_plugin_text( $theme->get( 'Name' ) ) : null,
				'version'      => $is_theme_object ? self::nullable_plugin_text( $theme->get( 'Version' ) ) : null,
				'status'       => $stylesheet === $active_stylesheet ? 'active' : 'inactive',
				'description'  => $is_theme_object ? self::nullable_plugin_text( $theme->get( 'Description' ), true ) : null,
				'author'       => $is_theme_object ? self::nullable_plugin_text( $theme->get( 'Author' ) ) : null,
				'template'     => $template,
			);
		}

		return new \WP_REST_Response( array( 'themes' => $theme_list ), 200 );
	}

	/**
	 * Check that a theme identifier is a safe, relative stylesheet or template name.
	 *
	 * @param string $identifier Theme stylesheet or template key from WordPress.
	 * @return bool Whether the identifier is safe to include in the response.
	 */
	private static function is_safe_theme_identifier( string $identifier ): bool {
		return '' !== $identifier
			&& \strlen( $identifier ) <= 255
			&& 1 !== \preg_match( '~[^A-Za-z0-9 _.-]~', $identifier )
			&& ! \str_contains( $identifier, '/' )
			&& ! \str_contains( $identifier, '\\' )
			&& '.' !== $identifier
			&& '..' !== $identifier;
	}

	/**
	 * Validate a bounded, positive posts page number.
	 *
	 * @param mixed           $value   Requested page value.
	 * @param \WP_REST_Request $request Current REST request.
	 * @param string          $param   Parameter name.
	 * @return bool Whether the value is within the supported range.
	 */
	public static function validate_posts_page( $value, \WP_REST_Request $request, string $param ): bool {
		return self::is_bounded_positive_integer( $value, self::MAX_POST_PAGE );
	}

	/**
	 * Validate the requested page size.
	 *
	 * @param mixed           $value   Requested page size.
	 * @param \WP_REST_Request $request Current REST request.
	 * @param string          $param   Parameter name.
	 * @return bool Whether the value is within the supported range.
	 */
	public static function validate_posts_per_page( $value, \WP_REST_Request $request, string $param ): bool {
		return self::is_bounded_positive_integer( $value, self::MAX_POSTS_PER_PAGE );
	}

	/**
	 * Validate that the requested post status is explicitly supported.
	 *
	 * @param mixed           $value   Requested post status.
	 * @param \WP_REST_Request $request Current REST request.
	 * @param string          $param   Parameter name.
	 * @return bool Whether the requested status is supported.
	 */
	public static function validate_post_status( $value, \WP_REST_Request $request, string $param ): bool {
		return \is_string( $value ) && \in_array( $value, self::POST_STATUSES, true );
	}

	/**
	 * Return posts and pagination metadata without modifying site content.
	 *
	 * @param \WP_REST_Request $request Current REST request.
	 * @return \WP_REST_Response Structured post listing.
	 */
	public static function get_posts( \WP_REST_Request $request ): \WP_REST_Response {
		$page     = (int) $request->get_param( 'page' );
		$per_page = (int) $request->get_param( 'per_page' );
		$status   = $request->get_param( 'status' );
		$query    = new \WP_Query(
			array(
				'post_type'           => 'post',
				'post_status'         => $status,
				'posts_per_page'      => $per_page,
				'paged'               => $page,
				'ignore_sticky_posts' => true,
				'no_found_rows'       => false,
				'orderby'             => 'date',
				'order'               => 'DESC',
			)
		);

		$posts = array();
		foreach ( $query->posts as $post ) {
			if ( ! $post instanceof \WP_Post || ! \in_array( $post->post_status, self::POST_STATUSES, true ) ) {
				continue;
			}

			$posts[] = self::serialize_post( $post );
		}

		$total_items = (int) $query->found_posts;
		$total_pages = $total_items > 0 ? (int) \ceil( $total_items / $per_page ) : 0;

		return new \WP_REST_Response(
			array(
				'connection_status' => 'connected',
				'posts'             => $posts,
				'pagination'        => array(
					'page'        => $page,
					'per_page'    => $per_page,
					'total_items' => $total_items,
					'total_pages' => $total_pages,
					'status'      => $status,
				),
				'message'           => 'Posts retrieved successfully.',
			),
			200
		);
	}

	/**
	 * Convert a post to the public allowlist used by SitePilot Core.
	 *
	 * @param \WP_Post $post WordPress post object.
	 * @return array<string, mixed> Safe post metadata only.
	 */
	private static function serialize_post( \WP_Post $post ): array {
		$category_ids = \wp_get_post_categories( $post->ID );
		$tag_terms    = \wp_get_post_tags( $post->ID );
		$categories   = \is_array( $category_ids ) ? \array_values( \array_filter( \array_map( 'absint', $category_ids ) ) ) : array();
		$tags         = array();

		if ( \is_array( $tag_terms ) ) {
			foreach ( $tag_terms as $tag ) {
				if ( \is_object( $tag ) && isset( $tag->term_id ) ) {
					$tags[] = \absint( $tag->term_id );
				}
			}
		}

		$link = \esc_url_raw( \get_permalink( $post ) );
		return array(
			'id'         => \absint( $post->ID ),
			'title'      => self::nullable_plugin_text( \get_the_title( $post ) ),
			'slug'       => '' !== $post->post_name ? \sanitize_title( $post->post_name ) : null,
			'status'     => $post->post_status,
			'author_id'  => \absint( $post->post_author ),
			'date'       => self::nullable_plugin_text( \get_post_time( DATE_W3C, false, $post ) ),
			'modified'   => self::nullable_plugin_text( \get_post_modified_time( DATE_W3C, false, $post ) ),
			'link'       => '' !== $link ? $link : null,
			'categories' => $categories,
			'tags'       => $tags,
		);
	}

	/**
	 * Return allowlisted page metadata and pagination without modifying site content.
	 *
	 * @param \WP_REST_Request $request Current REST request.
	 * @return \WP_REST_Response Structured page listing.
	 */
	public static function get_pages( \WP_REST_Request $request ): \WP_REST_Response {
		$page     = $request->get_param( 'page' );
		$per_page = $request->get_param( 'per_page' );
		$status   = $request->get_param( 'status' );
		if (
			! self::is_bounded_positive_integer( $page, self::MAX_POST_PAGE )
			|| ! self::is_bounded_positive_integer( $per_page, self::MAX_POSTS_PER_PAGE )
			|| ! \is_string( $status )
			|| ! \in_array( $status, self::POST_STATUSES, true )
		) {
			return new \WP_REST_Response(
				array(
					'connection_status' => 'invalid_request',
					'pages'             => null,
					'pagination'        => null,
					'message'           => 'Page list parameters are invalid.',
				),
				400
			);
		}

		$page     = (int) $page;
		$per_page = (int) $per_page;
		$query    = new \WP_Query(
			array(
				'post_type'      => 'page',
				'post_status'    => $status,
				'posts_per_page' => $per_page,
				'paged'          => $page,
				'no_found_rows'  => false,
				'orderby'        => array(
					'menu_order' => 'ASC',
					'title'      => 'ASC',
				),
			)
		);

		$pages = array();
		foreach ( $query->posts as $post ) {
			if (
				! $post instanceof \WP_Post
				|| 'page' !== $post->post_type
				|| ! \in_array( $post->post_status, self::POST_STATUSES, true )
			) {
				continue;
			}

			$pages[] = self::serialize_page( $post );
		}

		$total_items = (int) $query->found_posts;
		$total_pages = $total_items > 0 ? (int) \ceil( $total_items / $per_page ) : 0;

		return new \WP_REST_Response(
			array(
				'connection_status' => 'connected',
				'pages'             => $pages,
				'pagination'        => array(
					'page'        => $page,
					'per_page'    => $per_page,
					'total_items' => $total_items,
					'total_pages' => $total_pages,
					'status'      => $status,
				),
				'message'           => 'Pages retrieved successfully.',
			),
			200
		);
	}

	/**
	 * Convert a WordPress page to the public allowlist used by SitePilot Core.
	 *
	 * @param \WP_Post $post WordPress page object.
	 * @return array<string, mixed> Safe page metadata only.
	 */
	private static function serialize_page( \WP_Post $post ): array {
		$link = \esc_url_raw( \get_permalink( $post ) );
		return array(
			'id'         => \absint( $post->ID ),
			'title'      => self::nullable_plugin_text( \get_the_title( $post ) ),
			'slug'       => '' !== $post->post_name ? \sanitize_title( $post->post_name ) : null,
			'status'     => $post->post_status,
			'author_id'  => \absint( $post->post_author ),
			'date'       => self::nullable_plugin_text( \get_post_time( DATE_W3C, false, $post ) ),
			'modified'   => self::nullable_plugin_text( \get_post_modified_time( DATE_W3C, false, $post ) ),
			'link'       => '' !== $link ? $link : null,
			'parent_id'  => \absint( $post->post_parent ),
			'menu_order' => (int) $post->menu_order,
		);
	}

	/**
	 * Return allowlisted user metadata and pagination without modifying site data.
	 *
	 * @param \WP_REST_Request $request Current REST request.
	 * @return \WP_REST_Response Structured user listing.
	 */
	public static function get_users( \WP_REST_Request $request ): \WP_REST_Response {
		$page     = $request->get_param( 'page' );
		$per_page = $request->get_param( 'per_page' );
		if (
			! self::is_bounded_positive_integer( $page, self::MAX_USER_PAGE )
			|| ! self::is_bounded_positive_integer( $per_page, self::MAX_USERS_PER_PAGE )
		) {
			return new \WP_REST_Response(
				array(
					'connection_status' => 'invalid_request',
					'users'             => null,
					'pagination'        => null,
					'message'           => 'User list parameters are invalid.',
				),
				400
			);
		}

		$page     = (int) $page;
		$per_page = (int) $per_page;
		$query    = new \WP_User_Query(
			array(
				'number'      => $per_page,
				'paged'       => $page,
				'count_total' => true,
				'orderby'     => 'ID',
				'order'       => 'ASC',
			)
		);

		$users = array();
		foreach ( $query->get_results() as $user ) {
			if ( ! $user instanceof \WP_User ) {
				continue;
			}

			$users[] = self::serialize_user( $user );
		}

		$total_items = (int) $query->get_total();
		$total_pages = $total_items > 0 ? (int) \ceil( $total_items / $per_page ) : 0;

		return new \WP_REST_Response(
			array(
				'connection_status' => 'connected',
				'users'             => $users,
				'pagination'        => array(
					'page'        => $page,
					'per_page'    => $per_page,
					'total_items' => $total_items,
					'total_pages' => $total_pages,
				),
				'message'           => 'Users retrieved successfully.',
			),
			200
		);
	}

	/**
	 * Convert a WordPress user to the privacy-limited allowlist used by Core.
	 *
	 * @param \WP_User $user WordPress user object.
	 * @return array<string, mixed> Safe user metadata only.
	 */
	private static function serialize_user( \WP_User $user ): array {
		$username = \is_email( $user->user_login ) ? null : self::nullable_user_text( $user->user_login, 60 );
		$registered_timestamp = '' !== $user->user_registered ? \strtotime( $user->user_registered ) : false;
		$registered = false !== $registered_timestamp ? \gmdate( DATE_W3C, $registered_timestamp ) : null;
		$roles = array();
		foreach ( \is_array( $user->roles ) ? $user->roles : array() as $role ) {
			$role = \is_string( $role ) ? \sanitize_key( $role ) : '';
			if ( '' !== $role && 1 === \preg_match( '/\A[a-z0-9_-]{1,64}\z/', $role ) ) {
				$roles[] = $role;
			}
		}

		return array(
			'id'           => \absint( $user->ID ),
			'username'     => $username,
			'display_name' => self::nullable_user_text( $user->display_name, 512 ),
			'roles'        => \array_values( \array_unique( $roles ) ),
			'registered'   => $registered,
			'description'  => self::nullable_user_text( $user->description, 4096, true ),
		);
	}

	/**
	 * Sanitize user text and remove email addresses before returning it.
	 *
	 * @param mixed $value User-supplied text.
	 * @param int   $limit Maximum accepted text length.
	 * @param bool  $multiline Whether to preserve line breaks.
	 * @return string|null Sanitized text without email addresses.
	 */
	private static function nullable_user_text( $value, int $limit, bool $multiline = false ): ?string {
		$text = self::nullable_plugin_text( $value, $multiline );
		if ( null === $text ) {
			return null;
		}

		$text = \preg_replace( '/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i', '[email removed]', $text );
		$text = \is_string( $text ) ? \trim( $text ) : '';
		if ( '' === $text || \strlen( $text ) > $limit ) {
			return null;
		}
		return $text;
	}

	/**
	 * Return one page of built-in tags without changing taxonomy terms.
	 *
	 * @param \WP_REST_Request $request Current REST request.
	 * @return \WP_REST_Response Structured tag listing.
	 */
	public static function get_tags( \WP_REST_Request $request ): \WP_REST_Response {
		$page     = $request->get_param( 'page' );
		$per_page = $request->get_param( 'per_page' );
		if (
			! self::is_bounded_positive_integer( $page, self::MAX_TAG_PAGE )
			|| ! self::is_bounded_positive_integer( $per_page, self::MAX_TAGS_PER_PAGE )
		) {
			return new \WP_REST_Response(
				array(
					'connection_status' => 'invalid_request',
					'tags'              => null,
					'pagination'        => null,
					'message'           => 'Tag list parameters are invalid.',
				),
				400
			);
		}

		$page        = (int) $page;
		$per_page    = (int) $per_page;
		$total_terms = \get_terms(
			array(
				'taxonomy'               => 'post_tag',
				'hide_empty'             => false,
				'hierarchical'            => false,
				'fields'                  => 'count',
				'update_term_meta_cache' => false,
			)
		);
		if ( \is_wp_error( $total_terms ) || ! \is_numeric( $total_terms ) || (int) $total_terms < 0 ) {
			return new \WP_REST_Response(
				array(
					'connection_status' => 'unavailable',
					'tags'              => null,
					'pagination'        => null,
					'message'           => 'WordPress tags could not be retrieved safely.',
				),
				500
			);
		}

		$terms = \get_terms(
			array(
				'taxonomy'               => 'post_tag',
				'hide_empty'             => false,
				'hierarchical'            => false,
				'number'                  => $per_page,
				'offset'                  => ( $page - 1 ) * $per_page,
				'orderby'                 => 'term_id',
				'order'                   => 'ASC',
				'fields'                  => 'all',
				'update_term_meta_cache' => false,
			)
		);
		if ( \is_wp_error( $terms ) || ! \is_array( $terms ) ) {
			return new \WP_REST_Response(
				array(
					'connection_status' => 'unavailable',
					'tags'              => null,
					'pagination'        => null,
					'message'           => 'WordPress tags could not be retrieved safely.',
				),
				500
			);
		}

		$tags = array();
		foreach ( $terms as $term ) {
			if ( $term instanceof \WP_Term && 'post_tag' === $term->taxonomy ) {
				$tags[] = self::serialize_tag( $term );
			}
		}

		$total_items = (int) $total_terms;
		return new \WP_REST_Response(
			array(
				'connection_status' => 'connected',
				'tags'              => $tags,
				'pagination'        => array(
					'page'        => $page,
					'per_page'    => $per_page,
					'total_items' => $total_items,
					'total_pages' => $total_items > 0 ? (int) \ceil( $total_items / $per_page ) : 0,
				),
				'message'           => 'Tags retrieved successfully.',
			),
			200
		);
	}

	/**
	 * Serialize only allowlisted fields from a built-in post-tag term.
	 *
	 * @param \WP_Term $term Tag term.
	 * @return array<string, mixed> Safe tag metadata.
	 */
	private static function serialize_tag( \WP_Term $term ): array {
		return array(
			'id'          => \absint( $term->term_id ),
			'name'        => self::nullable_category_text( $term->name, 512 ),
			'slug'        => self::nullable_category_slug( $term->slug ),
			'description' => self::nullable_category_text( $term->description, 4096, true ),
			'count'       => \max( 0, (int) $term->count ),
		);
	}

	/**
	 * Return one page of built-in categories without changing taxonomy terms.
	 *
	 * @param \WP_REST_Request $request Current REST request.
	 * @return \WP_REST_Response Structured category listing.
	 */
	public static function get_categories( \WP_REST_Request $request ): \WP_REST_Response {
		$page     = $request->get_param( 'page' );
		$per_page = $request->get_param( 'per_page' );
		if (
			! self::is_bounded_positive_integer( $page, self::MAX_CATEGORY_PAGE )
			|| ! self::is_bounded_positive_integer( $per_page, self::MAX_CATEGORIES_PER_PAGE )
		) {
			return new \WP_REST_Response(
				array(
					'connection_status' => 'invalid_request',
					'categories'        => null,
					'pagination'        => null,
					'message'           => 'Category list parameters are invalid.',
				),
				400
			);
		}

		$page        = (int) $page;
		$per_page    = (int) $per_page;
		$total_terms = \get_terms(
			array(
				'taxonomy'     => 'category',
				'hide_empty'   => false,
				'hierarchical' => false,
				'fields'       => 'count',
			)
		);
		if ( \is_wp_error( $total_terms ) || ! \is_numeric( $total_terms ) || (int) $total_terms < 0 ) {
			return new \WP_REST_Response(
				array(
					'connection_status' => 'unavailable',
					'categories'        => null,
					'pagination'        => null,
					'message'           => 'WordPress categories could not be retrieved safely.',
				),
				500
			);
		}

		$terms = \get_terms(
			array(
				'taxonomy'     => 'category',
				'hide_empty'   => false,
				'hierarchical' => false,
				'number'       => $per_page,
				'offset'       => ( $page - 1 ) * $per_page,
				'orderby'      => 'term_id',
				'order'        => 'ASC',
				'fields'       => 'all',
			)
		);
		if ( \is_wp_error( $terms ) || ! \is_array( $terms ) ) {
			return new \WP_REST_Response(
				array(
					'connection_status' => 'unavailable',
					'categories'        => null,
					'pagination'        => null,
					'message'           => 'WordPress categories could not be retrieved safely.',
				),
				500
			);
		}

		$categories = array();
		foreach ( $terms as $term ) {
			if ( $term instanceof \WP_Term && 'category' === $term->taxonomy ) {
				$categories[] = self::serialize_category( $term );
			}
		}

		$total_items = (int) $total_terms;
		return new \WP_REST_Response(
			array(
				'connection_status' => 'connected',
				'categories'        => $categories,
				'pagination'        => array(
					'page'        => $page,
					'per_page'    => $per_page,
					'total_items' => $total_items,
					'total_pages' => $total_items > 0 ? (int) \ceil( $total_items / $per_page ) : 0,
				),
				'message'           => 'Categories retrieved successfully.',
			),
			200
		);
	}

	/**
	 * Serialize only documented fields from a built-in category term.
	 *
	 * @param \WP_Term $term Category term.
	 * @return array<string, mixed> Safe category metadata.
	 */
	private static function serialize_category( \WP_Term $term ): array {
		return array(
			'id'          => \absint( $term->term_id ),
			'name'        => self::nullable_category_text( $term->name, 512 ),
			'slug'        => self::nullable_category_slug( $term->slug ),
			'description' => self::nullable_category_text( $term->description, 4096, true ),
			'parent_id'   => \absint( $term->parent ),
			'count'       => \max( 0, (int) $term->count ),
		);
	}

	/**
	 * Sanitize category display text and remove markup rather than rendering it.
	 *
	 * @param mixed $value Untrusted term text.
	 * @param int   $limit Maximum length in bytes.
	 * @param bool  $multiline Whether to preserve line breaks.
	 * @return string|null Safe plain text or null when unavailable.
	 */
	private static function nullable_category_text( $value, int $limit, bool $multiline = false ): ?string {
		if ( ! \is_string( $value ) ) {
			return null;
		}
		$text = $multiline ? \sanitize_textarea_field( $value ) : \sanitize_text_field( $value );
		$text = \wp_strip_all_tags( $text, true );
		return '' !== $text && \strlen( $text ) <= $limit ? $text : null;
	}

	/**
	 * Sanitize a category slug to its WordPress identifier form.
	 *
	 * @param mixed $value Raw term slug.
	 * @return string|null Safe slug or null when unavailable.
	 */
	private static function nullable_category_slug( $value ): ?string {
		if ( ! \is_string( $value ) || '' === $value ) {
			return null;
		}
		$slug = \sanitize_title( $value );
		return '' !== $slug && \strlen( $slug ) <= 200 ? $slug : null;
	}

	/**
	 * Return a paginated, allowlisted comment listing without changing comments.
	 *
	 * @param \WP_REST_Request $request Current REST request.
	 * @return \WP_REST_Response Structured comment listing.
	 */
	public static function get_comments( \WP_REST_Request $request ): \WP_REST_Response {
		$page     = $request->get_param( 'page' );
		$per_page = $request->get_param( 'per_page' );
		$status   = $request->get_param( 'status' );
		if (
			! self::is_bounded_positive_integer( $page, self::MAX_COMMENT_PAGE )
			|| ! self::is_bounded_positive_integer( $per_page, self::MAX_COMMENTS_PER_PAGE )
			|| ! \is_string( $status )
			|| ! \in_array( $status, self::COMMENT_STATUSES, true )
		) {
			return new \WP_REST_Response(
				array(
					'connection_status' => 'invalid_request',
					'comments'          => null,
					'pagination'        => null,
					'message'           => 'Comment list parameters are invalid.',
				),
				400
			);
		}

		$page     = (int) $page;
		$per_page = (int) $per_page;
		$native_status = array(
			'approved' => 'approve',
			'pending'  => 'hold',
			'spam'     => 'spam',
			'trash'    => 'trash',
		)[ $status ];
		$query = new \WP_Comment_Query(
			array(
				'status'        => $native_status,
				'number'        => $per_page,
				'paged'         => $page,
				'count'         => false,
				'orderby'       => 'comment_date_gmt',
				'order'         => 'DESC',
				'no_found_rows' => false,
			)
		);

		$comments = array();
		foreach ( $query->comments as $comment ) {
			if ( ! $comment instanceof \WP_Comment ) {
				continue;
			}
			$serialized = self::serialize_comment( $comment );
			if ( $serialized['status'] === $status ) {
				$comments[] = $serialized;
			}
		}

		$total_items = (int) $query->found_comments;
		$total_pages = $total_items > 0 ? (int) \ceil( $total_items / $per_page ) : 0;
		return new \WP_REST_Response(
			array(
				'connection_status' => 'connected',
				'comments'          => $comments,
				'pagination'        => array(
					'page'        => $page,
					'per_page'    => $per_page,
					'total_items' => $total_items,
					'total_pages' => $total_pages,
					'status'      => $status,
				),
				'message'           => 'Comments retrieved successfully.',
			),
			200
		);
	}

	/**
	 * Return only approved public fields from a comment object.
	 *
	 * @param \WP_Comment $comment WordPress comment object.
	 * @return array<string, mixed> Safe comment fields.
	 */
	private static function serialize_comment( \WP_Comment $comment ): array {
		$raw_status = (string) $comment->comment_approved;
		$status = array(
			'1'     => 'approved',
			'0'     => 'pending',
			'spam'  => 'spam',
			'trash' => 'trash',
		)[ $raw_status ] ?? '';
		$author_name = self::nullable_comment_text( $comment->comment_author, 512 );
		$date = '' !== $comment->comment_date_gmt
			? \get_comment_date( DATE_W3C, $comment )
			: null;
		$content = self::nullable_comment_content( $comment->comment_content );
		$type = '' !== $comment->comment_type ? \sanitize_key( $comment->comment_type ) : 'comment';

		return array(
			'id'          => \absint( $comment->comment_ID ),
			'post_id'     => \absint( $comment->comment_post_ID ),
			'author_name' => $author_name,
			'date'        => self::nullable_plugin_text( $date ),
			'content'     => $content,
			'status'      => $status,
			'type'        => 1 === \preg_match( '/\A[a-z0-9_-]{1,64}\z/', $type ) ? $type : 'comment',
		);
	}

	/**
	 * Sanitize optional comment text and suppress email addresses.
	 *
	 * @param mixed $value Untrusted comment author text.
	 * @param int   $limit Maximum accepted length.
	 * @return string|null Safe text or null when unavailable.
	 */
	private static function nullable_comment_text( $value, int $limit ): ?string {
		$text = self::nullable_plugin_text( $value );
		if ( null === $text ) {
			return null;
		}
		$text = \preg_replace( '/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i', '[email removed]', $text );
		$text = \is_string( $text ) ? \trim( $text ) : '';
		return '' !== $text && \strlen( $text ) <= $limit ? $text : null;
	}

	/**
	 * Convert comment HTML to bounded plain text without rendering it.
	 *
	 * @param mixed $value Untrusted comment content.
	 * @return string|null Plain text or null when unavailable.
	 */
	private static function nullable_comment_content( $value ): ?string {
		$text = self::nullable_plugin_text( $value, true );
		if ( null === $text ) {
			return null;
		}
		$text = \wp_strip_all_tags( $text, true );
		$text = \sanitize_textarea_field( $text );
		$text = \wp_html_excerpt( $text, 2048, '' );
		$text = \preg_replace( '/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i', '[email removed]', $text );
		$text = \is_string( $text ) ? \trim( $text ) : '';
		return '' !== $text ? $text : null;
	}

	/**
	 * Return a paginated, allowlisted attachment listing without changing media.
	 *
	 * @param \WP_REST_Request $request Current REST request.
	 * @return \WP_REST_Response Structured media listing.
	 */
	public static function get_media( \WP_REST_Request $request ): \WP_REST_Response {
		$page     = $request->get_param( 'page' );
		$per_page = $request->get_param( 'per_page' );
		if (
			! self::is_bounded_positive_integer( $page, self::MAX_MEDIA_PAGE )
			|| ! self::is_bounded_positive_integer( $per_page, self::MAX_MEDIA_PER_PAGE )
		) {
			return new \WP_REST_Response(
				array(
					'connection_status' => 'invalid_request',
					'media'             => null,
					'pagination'        => null,
					'message'           => 'Media list parameters are invalid.',
				),
				400
			);
		}

		$page     = (int) $page;
		$per_page = (int) $per_page;
		$query    = new \WP_Query(
			array(
				'post_type'      => 'attachment',
				'post_status'    => 'inherit',
				'posts_per_page' => $per_page,
				'paged'          => $page,
				'no_found_rows'  => false,
				'orderby'        => 'date',
				'order'          => 'DESC',
			)
		);

		$media = array();
		foreach ( $query->posts as $attachment ) {
			if ( ! $attachment instanceof \WP_Post || 'attachment' !== $attachment->post_type ) {
				continue;
			}
			$media[] = self::serialize_media( $attachment );
		}

		$total_items = (int) $query->found_posts;
		$total_pages = $total_items > 0 ? (int) \ceil( $total_items / $per_page ) : 0;
		return new \WP_REST_Response(
			array(
				'connection_status' => 'connected',
				'media'             => $media,
				'pagination'        => array(
					'page'        => $page,
					'per_page'    => $per_page,
					'total_items' => $total_items,
					'total_pages' => $total_pages,
				),
				'message'           => 'Media retrieved successfully.',
			),
			200
		);
	}

	/**
	 * Serialize only the documented, non-sensitive attachment fields.
	 *
	 * @param \WP_Post $attachment WordPress attachment object.
	 * @return array<string, mixed> Safe attachment metadata.
	 */
	private static function serialize_media( \WP_Post $attachment ): array {
		$attached_file = \get_attached_file( $attachment->ID );
		$filename      = \is_string( $attached_file ) && '' !== $attached_file
			? \sanitize_file_name( \wp_basename( $attached_file ) )
			: null;
		if (
			null !== $filename
			&& ( '' === $filename || '.' === $filename || '..' === $filename
				|| \str_contains( $filename, '/' ) || \str_contains( $filename, '\\' ) || \str_contains( $filename, ':' ) )
		) {
			$filename = null;
		}

		$raw_mime = \get_post_mime_type( $attachment );
		$mime_type = \is_string( $raw_mime ) ? \strtolower( \sanitize_mime_type( $raw_mime ) ) : '';
		if ( 1 !== \preg_match( '~\A[a-z0-9][a-z0-9.+-]{0,62}/[a-z0-9][a-z0-9.+-]{0,62}\z~', $mime_type ) ) {
			$mime_type = null;
		}

		$media_type = 'file';
		if ( \wp_attachment_is_image( $attachment->ID ) || ( \is_string( $mime_type ) && \str_starts_with( $mime_type, 'image/' ) ) ) {
			$media_type = 'image';
		} elseif ( \is_string( $mime_type ) && \str_starts_with( $mime_type, 'video/' ) ) {
			$media_type = 'video';
		} elseif ( \is_string( $mime_type ) && \str_starts_with( $mime_type, 'audio/' ) ) {
			$media_type = 'audio';
		}

		$alt_text  = \get_post_meta( $attachment->ID, '_wp_attachment_image_alt', true );
		$source_url = \wp_get_attachment_url( $attachment->ID );
		$source_url = \is_string( $source_url ) ? self::safe_media_url( $source_url ) : null;

		return array(
			'id'          => \absint( $attachment->ID ),
			'title'       => self::nullable_media_text( \get_the_title( $attachment ), 1024 ),
			'slug'        => '' !== $attachment->post_name ? \sanitize_title( $attachment->post_name ) : null,
			'filename'    => $filename,
			'mime_type'   => $mime_type,
			'media_type'  => $media_type,
			'date'        => self::nullable_media_text( \get_post_time( DATE_W3C, false, $attachment ), 64 ),
			'modified'    => self::nullable_media_text( \get_post_modified_time( DATE_W3C, false, $attachment ), 64 ),
			'alt_text'    => self::nullable_media_text( $alt_text, 2048 ),
			'caption'     => self::nullable_media_text( $attachment->post_excerpt, 4096, true ),
			'description' => self::nullable_media_text( $attachment->post_content, 4096, true ),
			'source_url'  => $source_url,
		);
	}

	/**
	 * Sanitize optional attachment text and suppress values containing paths.
	 *
	 * @param mixed $value User-controlled attachment text.
	 * @param int   $limit Maximum accepted text length.
	 * @param bool  $multiline Whether line breaks are allowed.
	 * @return string|null Sanitized value, or null if missing or path-like.
	 */
	private static function nullable_media_text( $value, int $limit, bool $multiline = false ): ?string {
		$text = self::nullable_plugin_text( $value, $multiline );
		if ( null === $text || \strlen( $text ) > $limit ) {
			return null;
		}
		$has_windows_path = 1 === \preg_match( '~(?:^|[\s(=:])(?:[A-Z]:[\\/]|\\\\)~i', $text );
		$has_absolute_path = 1 === \preg_match( '~(?:^|[\s(=:])/(?!/)~', $text );
		return $has_windows_path || $has_absolute_path ? null : $text;
	}

	/**
	 * Allow only public HTTP(S) attachment URLs without URL credentials.
	 *
	 * @param string $url Attachment URL from WordPress.
	 * @return string|null Safe URL, or null when unavailable or invalid.
	 */
	private static function safe_media_url( string $url ): ?string {
		$url = \esc_url_raw( $url, array( 'http', 'https' ) );
		$parts = \wp_parse_url( $url );
		if (
			'' === $url
			|| ! \is_array( $parts )
			|| ! isset( $parts['scheme'], $parts['host'] )
			|| ! \in_array( \strtolower( $parts['scheme'] ), array( 'http', 'https' ), true )
			|| isset( $parts['user'] )
			|| isset( $parts['pass'] )
			|| isset( $parts['query'] )
			|| isset( $parts['fragment'] )
		) {
			return null;
		}
		return $url;
	}

	/**
	 * Validate a positive integer string or integer without coercing other input.
	 *
	 * @param mixed $value Requested integer value.
	 * @param int   $max   Maximum accepted value.
	 * @return bool Whether the value is a positive integer within the maximum.
	 */
	private static function is_bounded_positive_integer( $value, int $max ): bool {
		if ( \is_int( $value ) ) {
			return $value >= 1 && $value <= $max;
		}

		if ( ! \is_string( $value ) || 1 !== \preg_match( '/\A[0-9]+\z/', $value ) ) {
			return false;
		}

		$integer = (int) $value;
		return $integer >= 1 && $integer <= $max;
	}
}

\add_action( 'rest_api_init', array( Plugin::class, 'register_routes' ) );
